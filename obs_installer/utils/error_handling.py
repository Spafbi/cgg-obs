"""
Error Handling and Exception Management for OBS Installer

Provides comprehensive error handling, logging configuration, and
user-friendly error reporting throughout the application.
"""

import sys
import os
import logging
import traceback
from pathlib import Path
from typing import Optional, Callable, Any
from functools import wraps
import datetime

from PyQt6.QtWidgets import QMessageBox, QWidget
from PyQt6.QtCore import QObject, pyqtSignal


class ErrorHandler:
    """
    Centralized error handling and logging system.
    """
    
    def __init__(self, log_file: Optional[Path] = None):
        """
        Initialize the error handler.
        
        Args:
            log_file: Optional path to log file
        """
        if log_file is None:
            log_dir = Path.home() / 'obs-installer'
            log_dir.mkdir(parents=True, exist_ok=True)
            self.log_file = log_dir / 'obs_installer.log'
        else:
            self.log_file = log_file
        self.logger = logging.getLogger(__name__)
        self.setup_logging()
    
    def setup_logging(self):
        """Set up logging configuration."""
        # Create logs directory if needed
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        # Clear any existing handlers
        root_logger.handlers.clear()
        
        # File handler for detailed logging
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        # Console handler for development
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(levelname)s: %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # Log startup
        self.logger.info("Error handling initialized")
        self.logger.info(f"Log file: {self.log_file}")
    
    def handle_exception(self, exc_type, exc_value, exc_traceback):
        """
        Handle uncaught exceptions.
        
        Args:
            exc_type: Exception type
            exc_value: Exception value
            exc_traceback: Exception traceback
        """
        if issubclass(exc_type, KeyboardInterrupt):
            # Handle Ctrl+C gracefully
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        # Log the exception
        self.logger.critical(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
        
        # Show user-friendly error dialog
        self.show_critical_error(
            "Critical Error",
            f"An unexpected error occurred:\n\n{exc_value}\n\n"
            f"Please check the log file for details:\n{self.log_file}"
        )
    
    def show_error(self, parent: Optional[QWidget], title: str, message: str, 
                   details: Optional[str] = None):
        """
        Show an error dialog to the user.
        
        Args:
            parent: Parent widget
            title: Dialog title
            message: Error message
            details: Optional detailed error information
        """
        msg_box = QMessageBox(parent)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        
        if details:
            msg_box.setDetailedText(details)
        
        msg_box.exec()
        
        # Log the error
        self.logger.error(f"{title}: {message}")
        if details:
            self.logger.error(f"Details: {details}")
    
    def show_warning(self, parent: Optional[QWidget], title: str, message: str):
        """
        Show a warning dialog to the user.
        
        Args:
            parent: Parent widget
            title: Dialog title
            message: Warning message
        """
        QMessageBox.warning(parent, title, message)
        self.logger.warning(f"{title}: {message}")
    
    def show_critical_error(self, title: str, message: str):
        """
        Show a critical error dialog without parent.
        
        Args:
            title: Dialog title
            message: Error message
        """
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.exec()


def handle_errors(parent_widget: Optional[QWidget] = None, 
                 show_dialog: bool = True,
                 default_return: Any = None):
    """
    Decorator for handling exceptions in functions.
    
    Args:
        parent_widget: Parent widget for error dialogs
        show_dialog: Whether to show error dialog
        default_return: Default value to return on error
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger = logging.getLogger(func.__module__)
                logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
                
                if show_dialog:
                    from ..ui.main_window import QMessageBox
                    QMessageBox.critical(
                        parent_widget,
                        f"Error in {func.__name__}",
                        f"An error occurred:\n\n{str(e)}"
                    )
                
                return default_return
        return wrapper
    return decorator


class SafeOperationMixin:
    """
    Mixin class providing safe operation methods with error handling.
    """
    
    def safe_file_operation(self, operation: Callable, *args, **kwargs) -> tuple[bool, Optional[str]]:
        """
        Safely perform a file operation.
        
        Args:
            operation: Function to perform
            *args: Arguments for the operation
            **kwargs: Keyword arguments for the operation
            
        Returns:
            tuple: (success, error_message)
        """
        try:
            operation(*args, **kwargs)
            return True, None
        except PermissionError as e:
            return False, f"Permission denied: {e}"
        except FileNotFoundError as e:
            return False, f"File not found: {e}"
        except OSError as e:
            return False, f"File system error: {e}"
        except Exception as e:
            return False, f"Unexpected error: {e}"
    
    def safe_network_operation(self, operation: Callable, *args, **kwargs) -> tuple[bool, Optional[str]]:
        """
        Safely perform a network operation.
        
        Args:
            operation: Function to perform
            *args: Arguments for the operation
            **kwargs: Keyword arguments for the operation
            
        Returns:
            tuple: (success, error_message)
        """
        try:
            result = operation(*args, **kwargs)
            return True, result
        except ConnectionError as e:
            return False, f"Connection error: {e}"
        except TimeoutError as e:
            return False, f"Operation timed out: {e}"
        except Exception as e:
            return False, f"Network error: {e}"


class ErrorReporter(QObject):
    """
    Error reporter for sending error information.
    """
    
    error_reported = pyqtSignal(str, str)  # error_type, error_message
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
    
    def report_error(self, error_type: str, error_message: str, 
                    context: Optional[dict] = None):
        """
        Report an error.
        
        Args:
            error_type: Type of error
            error_message: Error message
            context: Additional context information
        """
        self.logger.error(f"Error reported - Type: {error_type}, Message: {error_message}")
        
        if context:
            self.logger.error(f"Context: {context}")
        
        self.error_reported.emit(error_type, error_message)


def validate_installation_path(path: str) -> tuple[bool, Optional[str]]:
    """
    Validate an installation path.
    
    Args:
        path: Path to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not path:
        return False, "Installation path cannot be empty"
    
    try:
        path_obj = Path(path)
        
        # Check if path is absolute
        if not path_obj.is_absolute():
            return False, "Installation path must be an absolute path"
        
        # Check if we can create the directory
        if not path_obj.exists():
            try:
                # Test if we can create the parent directory
                parent = path_obj.parent
                if not parent.exists():
                    # Try to create parent directories
                    parent.mkdir(parents=True, exist_ok=True)
                    # Remove test directory if we created it
                    if parent != path_obj:
                        parent.rmdir()
                
                # Test write access to parent
                if not os.access(parent, os.W_OK):
                    return False, "No write permission for the specified location"
                    
            except OSError as e:
                return False, f"Cannot create directory: {e}"
        else:
            # Path exists, check if it's a directory and writable
            if not path_obj.is_dir():
                return False, "Path exists but is not a directory"
            
            if not os.access(path_obj, os.W_OK):
                return False, "No write permission for the specified directory"
        
        # Check available disk space (at least 500MB)
        try:
            import shutil
            free_space = shutil.disk_usage(path_obj.parent if not path_obj.exists() else path_obj).free
            required_space = 500 * 1024 * 1024  # 500MB in bytes
            
            if free_space < required_space:
                return False, f"Insufficient disk space. Required: 500MB, Available: {free_space // (1024*1024)}MB"
                
        except Exception:
            # If we can't check disk space, just warn but don't fail
            pass
        
        return True, None
        
    except Exception as e:
        return False, f"Invalid path: {e}"


def setup_global_error_handling() -> ErrorHandler:
    """
    Set up global error handling for the application.
    
    Returns:
        ErrorHandler instance
    """
    try:
        # Create error handler
        error_handler = ErrorHandler()
        
        # Set up global exception handler
        sys.excepthook = error_handler.handle_exception
        
        # Log startup information
        logger = logging.getLogger(__name__)
        logger.info("=" * 50)
        logger.info("CGG OBS Studio Installer Starting")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Platform: {sys.platform}")
        logger.info(f"Working directory: {os.getcwd()}")
        logger.info("=" * 50)
        
        return error_handler
    except Exception as e:
        # Fallback error handling if ErrorHandler fails to initialize
        print(f"Warning: Could not initialize error handler: {e}")
        print("Continuing with basic error handling...")
        
        # Set up basic logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Create a minimal error handler
        class MinimalErrorHandler:
            def __init__(self):
                self.logger = logging.getLogger(__name__)
            
            def handle_exception(self, exc_type, exc_value, exc_traceback):
                if issubclass(exc_type, KeyboardInterrupt):
                    sys.__excepthook__(exc_type, exc_value, exc_traceback)
                    return
                self.logger.critical(
                    "Uncaught exception", 
                    exc_info=(exc_type, exc_value, exc_traceback)
                )
        
        minimal_handler = MinimalErrorHandler()
        sys.excepthook = minimal_handler.handle_exception
        
        return minimal_handler


def create_error_context(operation: str, **kwargs) -> dict:
    """
    Create error context information.
    
    Args:
        operation: Name of the operation
        **kwargs: Additional context information
        
    Returns:
        dict: Context information
    """
    context = {
        'operation': operation,
        'timestamp': datetime.datetime.now().isoformat(),
        'platform': sys.platform,
        'python_version': sys.version,
    }
    
    # Add any additional context
    context.update(kwargs)
    
    return context


# Global error handler instance
_global_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance."""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = setup_global_error_handling()
    return _global_error_handler