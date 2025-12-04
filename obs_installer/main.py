"""
CGG OBS Studio Installer - Main Application Entry Point

A Python 3.13+ application with Qt6 GUI for downloading and installing OBS Studio on Windows.

Features:
- Qt6-based modern user interface
- Automatic download of the latest OBS Studio release from GitHub
- Smart version checking to avoid unnecessary downloads
- Configurable installation location with persistent settings
- Progress tracking for downloads and extraction
- Comprehensive error handling and user feedback

Usage:
    python -m obs_installer.main
    
    Or if installed via pip:
    obs-installer
"""

import sys
import logging
from pathlib import Path


def test_resources():
    """Test resource accessibility (for bundled executable testing)."""
    try:
        from .utils.resources import verify_resources, log_resource_status
        
        print("=== CGG OBS Installer Resource Test ===")
        print()
        
        # Log detailed resource status
        log_resource_status()
        
        # Run verification
        results = verify_resources()
        
        print()
        print("=== Verification Summary ===")
        all_good = True
        for resource, available in results.items():
            status = "✓ PASS" if available else "✗ FAIL"
            print(f"{resource}: {status}")
            if not available:
                all_good = False
        
        print()
        if all_good:
            print("✓ All resources are accessible! The executable is ready to use.")
            return 0
        else:
            print("✗ Some resources are missing! The executable may not work correctly.")
            return 1
            
    except Exception as e:
        print(f"Error during resource test: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    """Main application entry point."""
    
    # Check for test mode
    if len(sys.argv) > 1 and sys.argv[1] == "--test-resources":
        return test_resources()
    
    try:
        # Set up error handling before importing Qt
        from .utils.error_handling import setup_global_error_handling
        error_handler = setup_global_error_handling()
        
        # Import Qt components after error handling is set up
        from .ui.main_window import create_application, MainWindow
        from .core.config import ConfigManager
        from .core.installer import InstallationController
        
        # Create Qt application
        app = create_application()
        
        # Initialize configuration manager
        config_manager = ConfigManager()
        
        # Create main window
        main_window = MainWindow(config_manager)
        
        # Create installation controller to integrate backend with UI
        controller = InstallationController(main_window, config_manager)
        
        # Show the main window
        main_window.show()
        
        # Log application startup
        logger = logging.getLogger(__name__)
        logger.info("CGG OBS Studio Installer started")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Platform: {sys.platform}")
        
        # Run the application
        exit_code = app.exec()
        
        logger.info(f"Application exiting with code: {exit_code}")
        return exit_code
        
    except ImportError as e:
        # Handle missing dependencies gracefully
        print(f"Error: Missing required dependency: {e}")
        print("Please install required packages with: pip install -r requirements.txt")
        return 1
        
    except Exception as e:
        # Handle any other startup errors
        print(f"Error starting application: {e}")
        import traceback
        print("Full traceback:")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())