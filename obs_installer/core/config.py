"""
Configuration Manager for OBS Installer

Handles persistent storage of user preferences including:
- Installation directory path
- Last known OBS Studio version
- Application settings

Uses ConfigParser for cross-platform compatibility and stores
configuration in the user's profile directory.
"""

import os
import configparser
from pathlib import Path
from typing import Optional, Dict, Any
import logging


class ConfigManager:
    """
    Manages application configuration and persistent user preferences.
    
    The configuration file is stored in the user's profile directory
    as '.obs_installer_config.ini' to maintain persistence across runs.
    """
    
    def __init__(self):
        """Initialize the configuration manager."""
        self.logger = logging.getLogger(__name__)
        
        # Define config file location in user profile obs-installer directory
        self.config_dir = Path.home() / 'obs-installer'
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / 'obs_installer_config.ini'
        
        # Initialize ConfigParser
        self.config = configparser.ConfigParser()
        
        # Default configuration values
        self.defaults = {
            'installation': {
                'install_path': str(Path.home() / 'obs'),
                'last_obs_version': '',
                'download_cache_dir': str(Path.home() / 'obs-installer' / 'cache'),
                'shortcut_name': 'Chaotic Good Gaming OBS',
                'selected_icon_path': ''
            },
            'github': {
                'personal_access_token': '',
                'save_token': 'false'
            },
            'ui': {
                'window_width': '800',
                'window_height': '600',
                'window_x': '-1',
                'window_y': '-1',
                'remember_window_size': 'true'
            },
            'general': {
                'check_for_updates': 'true',
                'show_debug_info': 'false',
                'download_plugins': 'true',
                'plugin_cleanup_days': '30'
            }
        }
        
        # Load existing configuration or create with defaults
        self.load_config()
    
    def load_config(self) -> None:
        """
        Load configuration from file or create with default values.
        
        If the configuration file doesn't exist, it will be created
        with default values. If it exists but is corrupted, it will
        be backed up and recreated.
        """
        try:
            if self.config_file.exists():
                self.logger.info(f"Loading configuration from {self.config_file}")
                self.config.read(self.config_file)
                
                # Validate that all required sections exist
                self._validate_config()
            else:
                self.logger.info("Configuration file not found, creating with defaults")
                self._create_default_config()
                
        except (configparser.Error, OSError) as e:
            self.logger.error(f"Error loading configuration: {e}")
            self._backup_corrupted_config()
            self._create_default_config()
    
    def _validate_config(self) -> None:
        """
        Validate that all required configuration sections and keys exist.
        
        Adds any missing sections or keys with default values.
        """
        config_updated = False
        
        for section_name, section_data in self.defaults.items():
            if not self.config.has_section(section_name):
                self.logger.info(f"Adding missing section: {section_name}")
                self.config.add_section(section_name)
                config_updated = True
            
            for key, default_value in section_data.items():
                if not self.config.has_option(section_name, key):
                    self.logger.info(f"Adding missing option: {section_name}.{key}")
                    self.config.set(section_name, key, default_value)
                    config_updated = True
        
        if config_updated:
            self.save_config()
    
    def _create_default_config(self) -> None:
        """Create configuration file with default values."""
        for section_name, section_data in self.defaults.items():
            self.config.add_section(section_name)
            for key, value in section_data.items():
                self.config.set(section_name, key, value)
        
        self.save_config()
        self.logger.info("Created default configuration")
    
    def _backup_corrupted_config(self) -> None:
        """Create a backup of corrupted configuration file."""
        if self.config_file.exists():
            backup_file = self.config_file.with_suffix('.ini.backup')
            try:
                self.config_file.rename(backup_file)
                self.logger.info(f"Backed up corrupted config to {backup_file}")
            except OSError as e:
                self.logger.error(f"Failed to backup corrupted config: {e}")
    
    def save_config(self) -> bool:
        """
        Save current configuration to file.
        
        Returns:
            bool: True if save was successful, False otherwise
        """
        try:
            # Ensure parent directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config.write(f)
            
            self.logger.debug(f"Configuration saved to {self.config_file}")
            return True
            
        except (OSError, configparser.Error) as e:
            self.logger.error(f"Failed to save configuration: {e}")
            return False
    
    def get_install_path(self) -> str:
        """
        Get the configured OBS installation path.
        
        Returns:
            str: The installation path
        """
        return self.config.get('installation', 'install_path', 
                              fallback=self.defaults['installation']['install_path'])
    
    def set_install_path(self, path: str) -> None:
        """
        Set the OBS installation path.
        
        Args:
            path: The new installation path
        """
        self.config.set('installation', 'install_path', path)
        self.save_config()
        self.logger.info(f"Installation path updated to: {path}")
    
    def get_last_obs_version(self) -> str:
        """
        Get the last known OBS Studio version.
        
        Returns:
            str: The last known version, empty string if none
        """
        return self.config.get('installation', 'last_obs_version',
                              fallback=self.defaults['installation']['last_obs_version'])
    
    def set_last_obs_version(self, version: str) -> None:
        """
        Set the last known OBS Studio version.
        
        Args:
            version: The OBS Studio version string
        """
        self.config.set('installation', 'last_obs_version', version)
        self.save_config()
        self.logger.info(f"Last OBS version updated to: {version}")
    
    def has_previous_obs_installation(self) -> bool:
        """
        Check if OBS Studio was previously installed by this installer.
        
        Returns:
            bool: True if a previous installation exists
        """
        # Check if we have a recorded version (indicates successful installation)
        last_version = self.get_last_obs_version()
        if not last_version:
            return False
            
        # Also check if the installation path has OBS executable
        install_path = Path(self.get_install_path())
        obs_exe = install_path / "bin" / "64bit" / "obs64.exe"
        return obs_exe.exists()
    
    def get_download_cache_dir(self) -> str:
        """
        Get the download cache directory path.
        
        Returns:
            str: The cache directory path
        """
        return self.config.get('installation', 'download_cache_dir',
                              fallback=self.defaults['installation']['download_cache_dir'])
    
    def set_download_cache_dir(self, path: str) -> None:
        """
        Set the download cache directory path.
        
        Args:
            path: The new cache directory path
        """
        self.config.set('installation', 'download_cache_dir', path)
        self.save_config()
    
    def get_shortcut_name(self) -> str:
        """
        Get the configured shortcut name.
        
        Returns:
            str: The shortcut name to use
        """
        return self.config.get('installation', 'shortcut_name',
                              fallback=self.defaults['installation']['shortcut_name'])
    
    def set_shortcut_name(self, name: str) -> None:
        """
        Set the shortcut name.
        
        Args:
            name: The name to use for shortcuts
        """
        self.config.set('installation', 'shortcut_name', name)
        self.save_config()
        self.logger.info(f"Shortcut name updated to: {name}")
    
    def get_selected_icon_path(self) -> str:
        """
        Get the configured selected icon path.
        
        Returns:
            str: The path to the selected icon file, empty string if none
        """
        return self.config.get('installation', 'selected_icon_path',
                              fallback=self.defaults['installation']['selected_icon_path'])
    
    def set_selected_icon_path(self, path: str) -> None:
        """
        Set the selected icon path.
        
        Args:
            path: The path to the selected icon file
        """
        self.config.set('installation', 'selected_icon_path', path)
        self.save_config()
        self.logger.info(f"Selected icon path updated to: {path}")
    
    def clear_selected_icon_path(self) -> None:
        """Clear the selected icon path."""
        self.config.set('installation', 'selected_icon_path', '')
        self.save_config()
        self.logger.info("Selected icon path cleared")
    
    def get_window_size(self) -> tuple[int, int]:
        """
        Get the saved window size.
        
        Returns:
            tuple: (width, height) in pixels
        """
        try:
            width = self.config.getint('ui', 'window_width')
            height = self.config.getint('ui', 'window_height')
            return (width, height)
        except (ValueError, configparser.Error):
            return (800, 600)  # Default size
    
    def set_window_size(self, width: int, height: int) -> None:
        """
        Save the window size.
        
        Args:
            width: Window width in pixels
            height: Window height in pixels
        """
        self.config.set('ui', 'window_width', str(width))
        self.config.set('ui', 'window_height', str(height))
        self.save_config()
    
    def get_window_position(self) -> tuple[int, int]:
        """
        Get the saved window position.
        
        Returns:
            tuple: (x, y) position in pixels, (-1, -1) if not set
        """
        try:
            x = self.config.getint('ui', 'window_x')
            y = self.config.getint('ui', 'window_y')
            return (x, y)
        except (ValueError, configparser.Error):
            return (-1, -1)  # Not set
    
    def set_window_position(self, x: int, y: int) -> None:
        """
        Save the window position.
        
        Args:
            x: Window x position in pixels
            y: Window y position in pixels
        """
        self.config.set('ui', 'window_x', str(x))
        self.config.set('ui', 'window_y', str(y))
        self.save_config()
    
    def should_remember_window_size(self) -> bool:
        """
        Check if window size should be remembered.
        
        Returns:
            bool: True if window size should be remembered
        """
        return self.config.getboolean('ui', 'remember_window_size', 
                                     fallback=True)
    
    def should_download_plugins(self) -> bool:
        """
        Check if plugins should be downloaded automatically.
        
        Returns:
            bool: True if plugins should be downloaded
        """
        return self.config.getboolean('general', 'download_plugins',
                                     fallback=self.defaults['general']['download_plugins'] == 'true')
    
    def set_download_plugins(self, enabled: bool) -> None:
        """
        Set whether plugins should be downloaded automatically.
        
        Args:
            enabled: Whether to download plugins
        """
        self.config.set('general', 'download_plugins', str(enabled).lower())
        self.save_config()
        self.logger.info(f"Plugin download setting updated to: {enabled}")
    
    def get_plugin_cleanup_days(self) -> int:
        """
        Get the number of days to keep old plugin files.
        
        Returns:
            int: Number of days to keep files
        """
        return self.config.getint('general', 'plugin_cleanup_days',
                                 fallback=int(self.defaults['general']['plugin_cleanup_days']))
    
    def get_config_value(self, section: str, key: str, 
                        fallback: Optional[str] = None) -> Optional[str]:
        """
        Get a configuration value by section and key.
        
        Args:
            section: Configuration section name
            key: Configuration key name
            fallback: Default value if key not found
            
        Returns:
            str or None: The configuration value
        """
        try:
            return self.config.get(section, key, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback
    
    def set_config_value(self, section: str, key: str, value: str) -> bool:
        """
        Set a configuration value.
        
        Args:
            section: Configuration section name
            key: Configuration key name
            value: Value to set
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.config.has_section(section):
                self.config.add_section(section)
            
            self.config.set(section, key, value)
            return self.save_config()
            
        except configparser.Error as e:
            self.logger.error(f"Failed to set config value {section}.{key}: {e}")
            return False
    
    # GitHub Token Management
    def get_github_token(self) -> str:
        """
        Get the saved GitHub Personal Access Token.
        
        Returns:
            str: The GitHub token, or empty string if not set
        """
        if self.get_save_github_token():
            return self.config.get('github', 'personal_access_token', fallback='')
        return ''
    
    def set_github_token(self, token: str):
        """
        Set the GitHub Personal Access Token.
        
        Args:
            token: The GitHub Personal Access Token
        """
        try:
            if not self.config.has_section('github'):
                self.config.add_section('github')
            self.config.set('github', 'personal_access_token', token)
            self.save_config()
            self.logger.info("GitHub token saved to configuration")
        except (OSError, ValueError) as e:
            self.logger.error(f"Failed to set GitHub token: {e}")
    
    def clear_github_token(self):
        """Clear the saved GitHub token."""
        try:
            if self.config.has_section('github'):
                self.config.set('github', 'personal_access_token', '')
                self.save_config()
                self.logger.info("GitHub token cleared from configuration")
        except (OSError, ValueError) as e:
            self.logger.error(f"Failed to clear GitHub token: {e}")
    
    def get_save_github_token(self) -> bool:
        """
        Get whether to save the GitHub token.
        
        Returns:
            bool: True if token should be saved, False otherwise
        """
        return self.config.getboolean('github', 'save_token', fallback=False)
    
    def set_save_github_token(self, save: bool):
        """
        Set whether to save the GitHub token.
        
        Args:
            save: Whether to save the token
        """
        try:
            if not self.config.has_section('github'):
                self.config.add_section('github')
            self.config.set('github', 'save_token', str(save).lower())
            if not save:
                # If we're not saving tokens, clear any existing token
                self.config.set('github', 'personal_access_token', '')
            self.save_config()
            self.logger.info(f"GitHub token save preference set to: {save}")
        except (OSError, ValueError) as e:
            self.logger.error(f"Failed to set GitHub token save preference: {e}")
    
    def export_config(self, file_path: Path) -> bool:
        """
        Export current configuration to a specified file.
        
        Args:
            file_path: Path to export the configuration to
            
        Returns:
            bool: True if export was successful, False otherwise
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                self.config.write(f)
            self.logger.info(f"Configuration exported to {file_path}")
            return True
        except OSError as e:
            self.logger.error(f"Failed to export configuration: {e}")
            return False
    
    def import_config(self, file_path: Path) -> bool:
        """
        Import configuration from a specified file.
        
        Args:
            file_path: Path to import the configuration from
            
        Returns:
            bool: True if import was successful, False otherwise
        """
        try:
            if not file_path.exists():
                self.logger.error(f"Config file not found: {file_path}")
                return False
            
            temp_config = configparser.ConfigParser()
            temp_config.read(file_path)
            
            # Validate imported config has required sections
            for section in self.defaults.keys():
                if not temp_config.has_section(section):
                    self.logger.error(f"Imported config missing section: {section}")
                    return False
            
            # Import was successful, replace current config
            self.config = temp_config
            self.save_config()
            self.logger.info(f"Configuration imported from {file_path}")
            return True
            
        except (OSError, configparser.Error) as e:
            self.logger.error(f"Failed to import configuration: {e}")
            return False