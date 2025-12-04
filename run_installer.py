#!/usr/bin/env python3
"""
CGG OBS Studio Installer Launcher Script

Simple script to launch the OBS installer from the root directory.
"""

import sys
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup logging before importing the main application
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import and run the main application
from obs_installer.main import main

if __name__ == "__main__":
    # Log resource status for debugging
    try:
        from obs_installer.utils.resources import log_resource_status
        log_resource_status()
    except Exception as e:
        logging.error(f"Failed to log resource status: {e}")
    
    sys.exit(main())