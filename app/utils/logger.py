import logging
import sys
from datetime import datetime
from typing import Optional

from app.config import settings


class ColoredFormatter(logging.Formatter):
    """Colored log formatter for console output"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        # Add color to levelname
        levelname = record.levelname
        if levelname in self.COLORS:
            colored_levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
            record.levelname = colored_levelname
        
        return super().format(record)


def setup_logging():
    """Setup logging configuration for the application"""
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.log_level.upper()))
    
    # Formatter
    if settings.debug:
        # Colored formatter for development
        formatter = ColoredFormatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        # Standard formatter for production
        formatter = logging.Formatter(
            fmt=settings.log_format,
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler for production
    if not settings.debug:
        try:
            file_handler = logging.FileHandler('app.log')
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            print(f"Failed to setup file logging: {e}")
    
    # Set levels for external libraries
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name"""
    return logging.getLogger(name)


class RequestLogger:
    """Context manager for request-specific logging"""
    
    def __init__(self, logger: logging.Logger, request_id: str, user_id: Optional[str] = None):
        self.logger = logger
        self.request_id = request_id
        self.user_id = user_id
        self.start_time = datetime.utcnow()
    
    def __enter__(self):
        self.info(f"Request started - ID: {self.request_id}, User: {self.user_id}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.utcnow() - self.start_time).total_seconds()
        if exc_type:
            self.error(f"Request failed - ID: {self.request_id}, Duration: {duration:.2f}s, Error: {exc_val}")
        else:
            self.info(f"Request completed - ID: {self.request_id}, Duration: {duration:.2f}s")
    
    def _format_message(self, message: str) -> str:
        """Format message with request context"""
        return f"[{self.request_id}] {message}"
    
    def debug(self, message: str):
        self.logger.debug(self._format_message(message))
    
    def info(self, message: str):
        self.logger.info(self._format_message(message))
    
    def warning(self, message: str):
        self.logger.warning(self._format_message(message))
    
    def error(self, message: str):
        self.logger.error(self._format_message(message))
    
    def critical(self, message: str):
        self.logger.critical(self._format_message(message))


def log_function_call(func):
    """Decorator to log function calls"""
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        func_name = func.__name__
        
        logger.debug(f"Calling {func_name} with args={args}, kwargs={kwargs}")
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"{func_name} completed successfully")
            return result
        except Exception as e:
            logger.error(f"{func_name} failed with error: {str(e)}")
            raise
    
    return wrapper


def log_async_function_call(func):
    """Decorator to log async function calls"""
    async def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        func_name = func.__name__
        
        logger.debug(f"Calling async {func_name} with args={args}, kwargs={kwargs}")
        
        try:
            result = await func(*args, **kwargs)
            logger.debug(f"Async {func_name} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Async {func_name} failed with error: {str(e)}")
            raise
    
    return wrapper
