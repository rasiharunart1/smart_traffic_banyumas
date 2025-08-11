"""
Enhanced error handling for Smart Traffic Counter
Provides graceful error handling and user-friendly error messages
"""

import traceback
import logging
from typing import Optional, Callable, Any
from functools import wraps


class TrafficCounterError(Exception):
    """Base exception for Traffic Counter application"""
    pass


class ModelLoadError(TrafficCounterError):
    """Exception raised when YOLO model fails to load"""
    pass


class CaptureError(TrafficCounterError):
    """Exception raised when screen capture fails"""
    pass


class DatabaseError(TrafficCounterError):
    """Exception raised when database operations fail"""
    pass


class ErrorHandler:
    """Centralized error handling with graceful degradation"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
    def handle_model_load_error(self, error: Exception, model_path: str) -> None:
        """Handle YOLO model loading errors with user-friendly messages"""
        error_msg = f"Failed to load YOLO model from '{model_path}'"
        
        if "No such file" in str(error):
            error_msg += "\n• Check that the model file exists"
            error_msg += "\n• Verify the file path is correct"
        elif "CUDA" in str(error):
            error_msg += "\n• CUDA/GPU related issue"
            error_msg += "\n• Try using CPU mode instead"
        elif "permission" in str(error).lower():
            error_msg += "\n• File permission denied"
            error_msg += "\n• Check file access permissions"
        
        self.logger.error(f"{error_msg}\nOriginal error: {error}")
        raise ModelLoadError(error_msg) from error
    
    def handle_capture_error(self, error: Exception, context: str = "") -> None:
        """Handle screen capture errors"""
        error_msg = f"Screen capture failed"
        if context:
            error_msg += f" during {context}"
            
        if "display" in str(error).lower():
            error_msg += "\n• Display/screen access issue"
            error_msg += "\n• Check display permissions"
        
        self.logger.error(f"{error_msg}\nOriginal error: {error}")
        raise CaptureError(error_msg) from error
    
    def handle_database_error(self, error: Exception, operation: str = "") -> None:
        """Handle database operation errors"""
        error_msg = f"Database operation failed"
        if operation:
            error_msg += f" during {operation}"
            
        if "connection" in str(error).lower():
            error_msg += "\n• Database connection issue"
            error_msg += "\n• Check database server status"
        elif "authentication" in str(error).lower():
            error_msg += "\n• Database authentication failed"
            error_msg += "\n• Check credentials"
        
        self.logger.error(f"{error_msg}\nOriginal error: {error}")
        raise DatabaseError(error_msg) from error
    
    def safe_execute(self, func: Callable, *args, **kwargs) -> tuple[bool, Any]:
        """
        Safely execute a function with error handling
        Returns (success: bool, result_or_error: Any)
        """
        try:
            result = func(*args, **kwargs)
            return True, result
        except Exception as e:
            self.logger.error(f"Error executing {func.__name__}: {e}")
            return False, e


def with_error_handling(error_handler: ErrorHandler):
    """Decorator for automatic error handling"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_handler.logger.error(
                    f"Error in {func.__name__}: {e}\n{traceback.format_exc()}"
                )
                raise
        return wrapper
    return decorator