import logging
import sys
from doeksu.config import CONFIG


def configure_logger(name: str = "doeksu"):
    """Configure and return the logger for the application."""
    logger = logging.getLogger(name)
    log_level = getattr(logging, CONFIG.LOG_LEVEL.upper())
    logger.setLevel(log_level)
    
    # Only add handler if it doesn't already exist (avoid duplicate handlers)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level)
        
        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


def create_logger(module_name: str):
    """Get a logger for a specific module with doeksu namespace."""
    logger = configure_logger(f"doeksu.{module_name}")
    # Prevent log propagation to parent logger to avoid duplicates
    logger.propagate = False
    return logger


# Initialize the main logger
logger = configure_logger()

__all__ = ["logger", "configure_logger", "get_logger"]
