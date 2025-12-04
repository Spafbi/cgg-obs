"""
Windows Shortcut Creation Utilities

Provides functionality to create desktop and start menu shortcuts for OBS Studio
on Windows systems. Uses Windows COM interfaces for proper shortcut creation.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, List, Tuple
import winshell
import win32com.client
from win32com.shell import shell, shellcon


class WindowsShortcutCreator:
    """
    Creates and manages Windows shortcuts for applications.
    
    Supports creating shortcuts on:
    - Desktop
    - Start Menu
    - Taskbar pinning (where supported)
    """
    
    def __init__(self):
        """Initialize the shortcut creator."""
        self.logger = logging.getLogger(__name__)
        
        # Common paths
        self.desktop_path = Path(winshell.desktop())
        self.start_menu_path = Path(winshell.start_menu())
        self.programs_path = self.start_menu_path / "Programs"
    
    def create_shortcut(self,
                       target_path: Path,
                       shortcut_name: str,
                       shortcut_location: Path,
                       icon_path: Optional[Path] = None,
                       icon_index: int = 0,
                       description: str = "",
                       working_directory: Optional[Path] = None,
                       arguments: str = "") -> bool:
        """
        Create a Windows shortcut (.lnk file).
        
        Args:
            target_path: Path to the executable to launch
            shortcut_name: Name for the shortcut (without .lnk extension)
            shortcut_location: Directory where the shortcut will be created
            icon_path: Path to icon file (optional)
            icon_index: Index of icon in icon file (default: 0)
            description: Description/tooltip for the shortcut
            working_directory: Working directory for the application
            arguments: Command line arguments to pass
            
        Returns:
            bool: True if shortcut was created successfully
        """
        try:
            # Ensure shortcut location exists
            shortcut_location.mkdir(parents=True, exist_ok=True)
            
            # Create shortcut file path
            if not shortcut_name.endswith('.lnk'):
                shortcut_name += '.lnk'
            shortcut_path = shortcut_location / shortcut_name
            
            # Create COM object for Windows Shell
            shell_obj = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell_obj.CreateShortCut(str(shortcut_path))
            
            # Set shortcut properties
            shortcut.Targetpath = str(target_path)
            
            if working_directory:
                shortcut.WorkingDirectory = str(working_directory)
            else:
                shortcut.WorkingDirectory = str(target_path.parent)
            
            if arguments:
                shortcut.Arguments = arguments
            
            if description:
                shortcut.Description = description
            
            if icon_path and icon_path.exists():
                shortcut.IconLocation = f"{icon_path},{icon_index}"
            
            # Save the shortcut
            shortcut.save()
            
            self.logger.info(f"Created shortcut: {shortcut_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create shortcut {shortcut_name}: {e}")
            return False
    
    def create_desktop_shortcut(self,
                               target_path: Path,
                               shortcut_name: str,
                               icon_path: Optional[Path] = None,
                               description: str = "") -> bool:
        """
        Create a desktop shortcut.
        
        Args:
            target_path: Path to the executable
            shortcut_name: Name for the shortcut
            icon_path: Optional icon file path
            description: Shortcut description
            
        Returns:
            bool: True if successful
        """
        return self.create_shortcut(
            target_path=target_path,
            shortcut_name=shortcut_name,
            shortcut_location=self.desktop_path,
            icon_path=icon_path,
            description=description
        )
    
    def create_start_menu_shortcut(self,
                                  target_path: Path,
                                  shortcut_name: str,
                                  program_folder: str = "OBS Studio",
                                  icon_path: Optional[Path] = None,
                                  description: str = "") -> bool:
        """
        Create a start menu shortcut.
        
        Args:
            target_path: Path to the executable
            shortcut_name: Name for the shortcut
            program_folder: Folder name in Programs menu
            icon_path: Optional icon file path
            description: Shortcut description
            
        Returns:
            bool: True if successful
        """
        start_menu_folder = self.programs_path / program_folder
        
        return self.create_shortcut(
            target_path=target_path,
            shortcut_name=shortcut_name,
            shortcut_location=start_menu_folder,
            icon_path=icon_path,
            description=description
        )
    
    def find_obs_executable(self, installation_path: Path) -> Optional[Path]:
        """
        Find the OBS Studio executable in the installation directory.
        
        Args:
            installation_path: OBS installation directory
            
        Returns:
            Path to obs64.exe or obs32.exe if found, None otherwise
        """
        possible_exe_paths = [
            installation_path / "bin" / "64bit" / "obs64.exe",
            installation_path / "bin" / "64bit" / "obs.exe",
            installation_path / "bin" / "32bit" / "obs32.exe",
            installation_path / "bin" / "32bit" / "obs.exe",
            installation_path / "obs64.exe",
            installation_path / "obs.exe"
        ]
        
        for exe_path in possible_exe_paths:
            if exe_path.exists():
                self.logger.info(f"Found OBS executable: {exe_path}")
                return exe_path
        
        self.logger.warning(f"Could not find OBS executable in {installation_path}")
        return None
    
    def find_obs_icons(self, installation_path: Path) -> List[Path]:
        """
        Find available icon files in the OBS installation.
        
        Args:
            installation_path: OBS installation directory
            
        Returns:
            List of paths to icon files
        """
        icon_extensions = ['.ico', '.png', '.bmp']
        icon_dirs = [
            installation_path / "data" / "obs-studio" / "images",
            installation_path / "images",
            installation_path / "icons",
            installation_path / "data" / "images",
            installation_path
        ]
        
        icons = []
        
        for icon_dir in icon_dirs:
            if icon_dir.exists():
                for ext in icon_extensions:
                    icons.extend(icon_dir.glob(f"*{ext}"))
                    icons.extend(icon_dir.glob(f"**/*{ext}"))
        
        # Remove duplicates and sort
        unique_icons = list(set(icons))
        unique_icons.sort(key=lambda x: x.name.lower())
        
        self.logger.info(f"Found {len(unique_icons)} icon files")
        return unique_icons
    
    def get_icon_info(self, icon_path: Path) -> Tuple[str, str]:
        """
        Get display information about an icon file.
        
        Args:
            icon_path: Path to the icon file
            
        Returns:
            Tuple of (display_name, description)
        """
        name = icon_path.stem
        size_info = ""
        
        try:
            # Try to get file size for additional info
            size = icon_path.stat().st_size
            if size < 1024:
                size_info = f" ({size} bytes)"
            elif size < 1024 * 1024:
                size_info = f" ({size // 1024} KB)"
            else:
                size_info = f" ({size // (1024 * 1024)} MB)"
        except:
            pass
        
        display_name = name.replace('_', ' ').replace('-', ' ').title()
        description = f"{display_name}{size_info}"
        
        return display_name, description
    
    def create_obs_shortcuts(self,
                           installation_path: Path,
                           icon_path: Optional[Path] = None,
                           create_desktop: bool = True,
                           create_start_menu: bool = True,
                           shortcut_name: str = "OBS Studio") -> Tuple[bool, List[str]]:
        """
        Create shortcuts for OBS Studio.
        
        Args:
            installation_path: OBS installation directory
            icon_path: Optional custom icon path
            create_desktop: Whether to create desktop shortcut
            create_start_menu: Whether to create start menu shortcut
            shortcut_name: Name for the shortcuts (default: "OBS Studio")
            
        Returns:
            Tuple of (success, list_of_error_messages)
        """
        errors = []
        
        # Find OBS executable
        obs_exe = self.find_obs_executable(installation_path)
        if not obs_exe:
            errors.append("Could not find OBS executable")
            return False, errors
        
        # Default icon if none specified
        if not icon_path:
            icons = self.find_obs_icons(installation_path)
            if icons:
                # Prefer obs.ico or similar
                for icon in icons:
                    if 'obs' in icon.name.lower() and icon.suffix.lower() == '.ico':
                        icon_path = icon
                        break
                if not icon_path:
                    icon_path = icons[0]  # Use first available icon
        
        success = True
        
        # Create desktop shortcut
        if create_desktop:
            desktop_success = self.create_desktop_shortcut(
                target_path=obs_exe,
                shortcut_name=shortcut_name,
                icon_path=icon_path,
                description="Open Broadcaster Software Studio"
            )
            if not desktop_success:
                errors.append("Failed to create desktop shortcut")
                success = False
        
        # Create start menu shortcut
        if create_start_menu:
            start_menu_success = self.create_start_menu_shortcut(
                target_path=obs_exe,
                shortcut_name=shortcut_name,
                program_folder="OBS Studio",
                icon_path=icon_path,
                description="Open Broadcaster Software Studio"
            )
            if not start_menu_success:
                errors.append("Failed to create start menu shortcut")
                success = False
        
        return success, errors
    
    def remove_obs_shortcuts(self) -> Tuple[bool, List[str]]:
        """
        Remove existing OBS Studio shortcuts.
        
        Returns:
            Tuple of (success, list_of_error_messages)
        """
        errors = []
        success = True
        
        shortcuts_to_remove = [
            self.desktop_path / "OBS Studio.lnk",
            self.programs_path / "OBS Studio" / "OBS Studio.lnk"
        ]
        
        for shortcut_path in shortcuts_to_remove:
            try:
                if shortcut_path.exists():
                    shortcut_path.unlink()
                    self.logger.info(f"Removed shortcut: {shortcut_path}")
            except Exception as e:
                error_msg = f"Failed to remove {shortcut_path}: {e}"
                errors.append(error_msg)
                self.logger.error(error_msg)
                success = False
        
        # Try to remove empty start menu folder
        try:
            start_menu_folder = self.programs_path / "OBS Studio"
            if start_menu_folder.exists() and not any(start_menu_folder.iterdir()):
                start_menu_folder.rmdir()
                self.logger.info("Removed empty start menu folder")
        except Exception as e:
            self.logger.warning(f"Could not remove start menu folder: {e}")
        
        return success, errors


def create_obs_shortcuts_simple(installation_path: str,
                               icon_path: Optional[str] = None,
                               desktop: bool = True,
                               start_menu: bool = True) -> bool:
    """
    Simple function to create OBS shortcuts.
    
    Args:
        installation_path: Path to OBS installation
        icon_path: Optional path to icon file
        desktop: Create desktop shortcut
        start_menu: Create start menu shortcut
        
    Returns:
        bool: True if successful
    """
    try:
        creator = WindowsShortcutCreator()
        icon_path_obj = Path(icon_path) if icon_path else None
        
        success, errors = creator.create_obs_shortcuts(
            installation_path=Path(installation_path),
            icon_path=icon_path_obj,
            create_desktop=desktop,
            create_start_menu=start_menu
        )
        
        if errors:
            logging.getLogger(__name__).warning(f"Shortcut creation errors: {errors}")
        
        return success
        
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to create shortcuts: {e}")
        return False