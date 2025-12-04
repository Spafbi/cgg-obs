"""
Resource Path Utilities

Handles resource path resolution for both development and bundled executable environments.
"""

import sys
import os
from pathlib import Path
from typing import Union


def get_resource_path(relative_path: Union[str, Path]) -> Path:
    """
    Get the absolute path to a resource file or directory.
    
    This function handles both development and PyInstaller bundled environments:
    - In development: Resources are relative to the project root
    - In bundled executable: Resources are extracted to a temporary directory
    
    Args:
        relative_path: Path relative to the project root (e.g., "icons", "plugins.json")
        
    Returns:
        Path: Absolute path to the resource
    """
    relative_path = Path(relative_path)
    
    # Check if we're running as a PyInstaller bundle
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller bundle - resources are in the temporary extraction directory
        base_path = Path(sys._MEIPASS)
        resource_path = base_path / relative_path
        
        # Log for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Bundled mode: Looking for resource at {resource_path}")
        
        return resource_path
    else:
        # Development mode - find project root and construct path
        # Start from this file's directory and go up to find project root
        current_file = Path(__file__)
        
        # Navigate up to find the project root (where plugins.json and icons/ should be)
        project_root = current_file.parent.parent  # From utils/ to project root
        
        # Verify we found the right directory by checking for known files
        if not (project_root / "plugins.json").exists():
            # Try going up one more level
            project_root = project_root.parent
            
        resource_path = project_root / relative_path
        
        # Log for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Development mode: Looking for resource at {resource_path}")
        logger.debug(f"Project root detected as: {project_root}")
        
        return resource_path


def get_icons_directory() -> Path:
    """
    Get the path to the icons directory.
    
    Returns:
        Path: Path to the icons directory
    """
    return get_resource_path("icons")


def get_plugins_json_path() -> Path:
    """
    Get the path to the plugins.json file.
    
    Returns:
        Path: Path to the plugins.json file
    """
    return get_resource_path("plugins.json")


def list_available_icons() -> list[Path]:
    """
    Get a list of all available icon files.
    
    Returns:
        list[Path]: List of paths to available icon files
    """
    icons_dir = get_icons_directory()
    
    if not icons_dir.exists():
        return []
    
    # Supported icon formats
    icon_extensions = ['.ico', '.png', '.jpg', '.jpeg', '.bmp', '.gif']
    
    icons = []
    for ext in icon_extensions:
        # Find files with this extension
        icons.extend(icons_dir.glob(f"*{ext}"))
        # Also search subdirectories
        icons.extend(icons_dir.glob(f"**/*{ext}"))
    
    # Remove duplicates and sort
    unique_icons = sorted(list(set(icons)))
    
    return unique_icons


def verify_resources() -> dict[str, bool]:
    """
    Verify that all required resources are accessible.
    
    Returns:
        dict[str, bool]: Dictionary mapping resource names to availability status
    """
    results = {}
    
    # Check icons directory
    icons_dir = get_icons_directory()
    results['icons_directory'] = icons_dir.exists() and icons_dir.is_dir()
    
    # Check plugins.json
    plugins_json = get_plugins_json_path()
    results['plugins_json'] = plugins_json.exists() and plugins_json.is_file()
    
    # Check if we have any icons
    available_icons = list_available_icons()
    results['has_icons'] = len(available_icons) > 0
    
    return results


def log_resource_status():
    """
    Log the current resource status for debugging.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("=== Resource Status ===")
    logger.info(f"Running mode: {'Bundled' if hasattr(sys, '_MEIPASS') else 'Development'}")
    
    if hasattr(sys, '_MEIPASS'):
        logger.info(f"Bundle temp directory: {sys._MEIPASS}")
    
    status = verify_resources()
    for resource, available in status.items():
        status_text = "✓ Available" if available else "✗ Missing"
        logger.info(f"{resource}: {status_text}")
    
    # Log specific paths
    logger.info(f"Icons directory: {get_icons_directory()}")
    logger.info(f"Plugins JSON: {get_plugins_json_path()}")
    
    # Log available icons
    icons = list_available_icons()
    if icons:
        logger.info(f"Available icons ({len(icons)}):")
        for icon in icons:
            logger.info(f"  - {icon.name}")
    else:
        logger.warning("No icons found!")
    
    logger.info("======================")