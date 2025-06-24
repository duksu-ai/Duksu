import logging
import sys
from doeksu.config import CONFIG


def configure_logger():
    """Configure and return the logger for the application."""
    logger = logging.getLogger("doeksu")
    log_level = getattr(logging, CONFIG.LOG_LEVEL.upper())
    logger.setLevel(log_level)
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    
    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger


# Initialize the logger
logger = configure_logger()

__all__ = ["logger", "configure_logger"]
