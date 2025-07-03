from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuration class for environment variables"""

    # Database Settings
    @property
    def DATABASE_URL(self) -> str:
        return os.getenv('DATABASE_URL', 'postgresql+psycopg2://postgres:1234@localhost/doeksu')

    # Object Store Settings
    @property
    def OBJECT_STORE_TYPE(self) -> str:
        """Object store type: 'local' or 's3'"""
        return os.getenv('OBJECT_STORE_TYPE', 'local')

    @property
    def OBJECT_STORE_BASE_PATH(self) -> str:
        """Base path for local file system object store"""
        return os.getenv('OBJECT_STORE_BASE_PATH', 'storage/objects')

    # S3 Object Store Settings
    @property
    def S3_BUCKET_NAME(self) -> Optional[str]:
        """S3 bucket name for object storage"""
        return os.getenv('S3_BUCKET_NAME')

    @property
    def S3_REGION(self) -> str:
        """S3 region"""
        return os.getenv('S3_REGION', 'us-east-1')

    @property
    def S3_ACCESS_KEY_ID(self) -> Optional[str]:
        """S3 access key ID"""
        return os.getenv('S3_ACCESS_KEY_ID')

    @property
    def S3_SECRET_ACCESS_KEY(self) -> Optional[str]:
        """S3 secret access key"""
        return os.getenv('S3_SECRET_ACCESS_KEY')

    @property
    def S3_ENDPOINT_URL(self) -> Optional[str]:
        """S3 endpoint URL (for S3-compatible services like MinIO)"""
        return os.getenv('S3_ENDPOINT_URL')


CONFIG = Config()

__all__ = ["CONFIG"]
