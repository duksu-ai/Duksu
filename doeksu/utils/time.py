from datetime import datetime
from email.utils import parsedate_to_datetime
import re
import time

from doeksu.logging_config import logger


def parse_age_literal_to_seconds(age_literal: str) -> int:
    """Parse age cap string (e.g., '1d', '2m', '1y') to seconds."""
    pattern = r'^(\d+)(m|d|y)$'
    match = re.match(pattern, age_literal.lower())
    
    if not match:
        raise ValueError(f"Invalid age cap format: {age_literal}. Expected format: Nm, Nd, or Nyr (e.g., '1m', '30d', '1y')")
    
    value, unit = match.groups()
    value = int(value)
    
    if unit == 'm':
        return value * 30 * 24 * 60 * 60  # months (approximate)
    elif unit == 'd':
        return value * 24 * 60 * 60  # days
    elif unit == 'y':
        return value * 365 * 24 * 60 * 60  # years (approximate)
    
    raise ValueError(f"Unsupported time unit: {unit}")


def convert_date_str_to_timestamp(date_str: str) -> int:
    """Parse RSS published date string to unix timestamp."""
    if not date_str:
        return int(time.time())  # Current time as fallback
    
    try:
        # Try parsing RFC 2822 format (common in RSS)
        dt = parsedate_to_datetime(date_str)
        return int(dt.timestamp())
    except Exception:
        try:
            # Try ISO format
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return int(dt.timestamp())
        except Exception:
            logger.warning(f"Could not parse date '{date_str}', using current time")
            return int(time.time())