import logging
import sys
import os
from logging.handlers import RotatingFileHandler
from colorama import init, Fore, Style

# Initialize colorama for cross-platform color support
init(autoreset=True)

class ColoredFormatter(logging.Formatter):
    """Custom formatter providing colorized log output to the terminal."""
    
    COLORS = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Style.BRIGHT
    }

    def format(self, record):
        log_color = self.COLORS.get(record.levelno, Fore.WHITE)
        # Format the time and level
        time_str = self.formatTime(record, self.datefmt)
        level_name = f"{record.levelname:<8}"
        message = super().formatMessage(record)
        
        # Colorize the whole line or just parts as desired
        return f"{Style.DIM}[{time_str}]{Style.RESET_ALL} {log_color}{level_name}{Style.RESET_ALL} | {message}"


def get_logger(name="ASTRA"):
    """
    Retrieves or creates a centralized logger for ASTRA.
    Includes both console and file handlers.
    """
    logger = logging.getLogger(name)
    
    # If logger already has handlers, return it to avoid duplication
    if logger.hasHandlers():
        return logger
        
    logger.setLevel(logging.DEBUG)  # Capture everything; handlers will filter

    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "astra_system.log")

    # File handler: Keep 5 rotated logs of 5MB each
    file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)-8s] %(name)s (%(filename)s:%(lineno)d): %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_fmt)

    # Console handler: Colorized output for terminal
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO) # Default to INFO for console
    console_fmt = ColoredFormatter(
        fmt="%(message)s", 
        datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(console_fmt)

    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Prevent propagation to the root logger to avoid double logging
    logger.propagate = False

    return logger

# Create a default instance that can be imported directly
logger = get_logger("ASTRA")
