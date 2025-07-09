import json
import os
import hashlib
import asyncio
import boto3
from pathlib import Path
from typing import Any, Dict, Optional
from abc import ABC, abstractmethod
from pathvalidate import sanitize_filename
from ..config import CONFIG


class ObjectStoreBackend(ABC):
    """Abstract base class for object store backends."""
    
    @abstractmethod
    async def save_content(self, content: str, path: str, metadata: dict) -> str:
        """Save content and return the storage path/URL."""
        pass
    
    @abstractmethod
    async def read_content(self, path: str) -> Optional[str]:
        """Read content from storage path."""
        pass


class LocalFileSystemBackend(ObjectStoreBackend):
    """Local filesystem backend for object storage."""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.html_path = self.base_path / "html"
        self.markdown_path = self.base_path / "markdown"
    
    async def save_content(self, content: str, path: str, metadata: dict) -> str:
        """Save content to local file system."""
        file_path = self.base_path / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Add metadata to content based on file type
        if path.endswith('.html'):
            content_with_metadata = f"""<!-- 
Article URL: {metadata.get('article_url', '')}
Saved at: {file_path}
-->
{content}"""
        else:  # markdown
            content_with_metadata = f"""---
article_url: {metadata.get('article_url', '')}
saved_at: {file_path}
---

{content}"""
        
        # Save asynchronously
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, 
            lambda: file_path.write_text(content_with_metadata, encoding='utf-8')
        )
        
        return str(file_path.relative_to(self.base_path.parent))
    
    async def read_content(self, path: str) -> Optional[str]:
        """Read content from local file system."""
        try:
            full_path = self.base_path.parent / path
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(
                None, 
                lambda: full_path.read_text(encoding='utf-8')
            )
            return content
        except (FileNotFoundError, IOError):
            return None


class S3Backend(ObjectStoreBackend):
    """S3 backend for object storage."""
    
    def __init__(self, base_path: str):
        # Initialize S3 client
        session = boto3.Session(
            aws_access_key_id=CONFIG.S3_ACCESS_KEY_ID,
            aws_secret_access_key=CONFIG.S3_SECRET_ACCESS_KEY,
            region_name=CONFIG.S3_REGION
        )
        
        self.s3_client = session.client(
            's3',
            endpoint_url=CONFIG.S3_ENDPOINT_URL
        )
        
        self.bucket_name = CONFIG.S3_BUCKET_NAME
        self.path_prefix = base_path
        
        if not self.bucket_name:
            raise ValueError("S3_BUCKET_NAME must be configured for S3 backend")
    
    def _get_s3_key(self, path: str) -> str:
        """Generate S3 key with prefix."""
        return f"{self.path_prefix}/{path}" if self.path_prefix else path
    
    async def save_content(self, content: str, path: str, metadata: dict) -> str:
        """Save content to S3."""
        s3_key = self._get_s3_key(path)
        
        # Add metadata to content based on file type
        if path.endswith('.html'):
            content_with_metadata = f"""<!-- 
Article URL: {metadata.get('article_url', '')}
S3 Key: {s3_key}
-->
{content}"""
            content_type = 'text/html'
        else:  # markdown
            content_with_metadata = f"""---
article_url: {metadata.get('article_url', '')}
s3_key: {s3_key}
---

{content}"""
            content_type = 'text/markdown'
        
        # Upload to S3 asynchronously
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=content_with_metadata.encode('utf-8'),
                ContentType=content_type,
                Metadata={
                    'article_url': metadata.get('article_url', ''),
                    'content_type': content_type
                }
            )
        )
        
        return s3_key
    
    async def read_content(self, path: str) -> Optional[str]:
        """Read content from S3."""
        try:
            s3_key = self._get_s3_key(path) if not path.startswith(self.path_prefix) else path
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            )
            
            content = response['Body'].read().decode('utf-8')
            return content
        except self.s3_client.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return None
            raise
        except Exception:
            return None


class ObjectStore:
    """
    Object store for saving HTML and markdown content with configurable backends.
    """
    
    def __init__(self, prefix: str = ""):
        self.backend = self._create_backend(prefix)
    
    def _create_backend(self, prefix: str = "") -> ObjectStoreBackend:
        """Create the appropriate backend based on configuration."""
        store_type = CONFIG.OBJECT_STORE_TYPE.lower()
        base_path = CONFIG.OBJECT_STORE_BASE_PATH
        if prefix:
            base_path += f"/{prefix}"
        
        if store_type == 'local':
            base_path = f"local/{base_path}"
            return LocalFileSystemBackend(base_path)
        elif store_type == 's3':
            return S3Backend(base_path)
        else:
            raise ValueError(f"Unsupported object store type: {store_type}")
    
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to be safe for file systems and S3 keys."""
        sanitized = sanitize_filename(filename, replacement_text="_")
        sanitized = sanitized.replace(' ', '_')
        if len(sanitized) > 200:
            sanitized = sanitized[:200]
        return sanitized.strip('_')

    def generate_unique_filename(self, content: str, extension: str) -> str:
        """Generate a unique filename based on content hash."""
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        return f"{content_hash}.{extension}"
    
    async def save_html(self, content: str, filename: Optional[str] = None, metadata: Dict[str, Any] = {}) -> str:
        """
        Save HTML content and return the storage path.
        
        Args:
            content: HTML content to save
            filename: Optional filename (will be sanitized)
            metadata: Additional metadata
            
        Returns:
            Storage path/key for the saved HTML file
        """
        if not content:
            return ""
        
        if filename:
            sanitized_filename = self.sanitize_filename(filename)
            filename = f"{sanitized_filename}.html"
        else:
            filename = self.generate_unique_filename(content, "html")
        
        path = f"html/{filename}"
        
        return await self.backend.save_content(
            content, 
            path, 
            metadata
        )
    
    async def save_markdown(self, content: str, filename: Optional[str] = None, metadata: Dict[str, Any] = {}) -> str:
        """
        Save markdown content and return the storage path.
        
        Args:
            content: Markdown content to save
            filename: Optional filename (will be sanitized)
            metadata: Additional metadata
            
        Returns:
            Storage path/key for the saved markdown file
        """
        if not content:
            return ""
        
        if filename:
            sanitized_filename = self.sanitize_filename(filename)
            filename = f"{sanitized_filename}.md"
        else:
            filename = self.generate_unique_filename(content, "md")
        
        path = f"markdown/{filename}"
        
        return await self.backend.save_content(
            content, 
            path, 
            metadata
        )

    async def save_json(self, content: Dict[str, Any], filename: Optional[str] = None, metadata: Dict[str, Any] = {}) -> str:
        if not content:
            return ""
        
        if filename:
            sanitized_filename = self.sanitize_filename(filename)
            filename = f"{sanitized_filename}.json"
        else:
            filename = self.generate_unique_filename(json.dumps(content), "json")
        
        path = f"json/{filename}"
        
        return await self.backend.save_content(
            json.dumps(content),
            path,
            metadata
        )

# Global instance
object_store = ObjectStore()
