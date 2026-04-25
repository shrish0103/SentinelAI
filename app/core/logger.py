import logging
import sys
from typing import Optional

def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Initializes and configures the root logger for the entire application.
    Returns the root logger instance.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure the root logger
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
        force=True # Ensures we override any existing basic config
    )
    
    logger = logging.getLogger("sentinel-ai")
    logger.info(f"System Logging Initialized (Level: {log_level.upper()})")
    
    return logger

def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Returns a logger instance for a specific module.
    Use this across the project for consistent naming.
    """
    base_name = "sentinel-ai"
    if name:
        return logging.getLogger(f"{base_name}.{name}")
    return logging.getLogger(base_name)
