"""
OBS Plugin Manager

Handles downloading and managing OBS Studio plugins from various sources:
- GitHub repositories via GitHub API
- OBS Project forum resources
"""

import json
import logging
import re
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import requests
from urllib.parse import urlparse
from fnmatch import fnmatch

try:
    import py7zr
    HAS_PY7ZR = True
except ImportError:
    HAS_PY7ZR = False
    py7zr = None

try:
    from bs4 import BeautifulSoup
    HAS_BEAUTIFULSOUP = True
except ImportError:
    HAS_BEAUTIFULSOUP = False
    BeautifulSoup = None

from ..core.config import ConfigManager
from .downloader import FileDownloader, DownloadProgress


class PluginInfo:
    """Information about a plugin."""
    
    def __init__(self, name: str, filename_pattern: str, source_type: str, source_path: str, 
                 release: Optional[str] = None):
        self.name = name
        self.filename_pattern = filename_pattern
        self.source_type = source_type  # 'github' or 'obsproject'
        self.source_path = source_path
        self.release = release  # Specific release if specified
        
    def __repr__(self):
        return f"PluginInfo(name='{self.name}', source='{self.source_type}:{self.source_path}')"


class PluginVersion:
    """Version information for a downloaded plugin."""
    
    def __init__(self, name: str, version: str, release_date: str, download_url: str, 
                 local_path: Path):
        self.name = name
        self.version = version
        self.release_date = release_date
        self.download_url = download_url
        self.local_path = local_path
        self.downloaded_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'name': self.name,
            'version': self.version,
            'release_date': self.release_date,
            'download_url': self.download_url,
            'local_path': str(self.local_path),
            'downloaded_at': self.downloaded_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PluginVersion':
        """Create from dictionary."""
        instance = cls(
            name=data['name'],
            version=data['version'],
            release_date=data['release_date'],
            download_url=data['download_url'],
            local_path=Path(data['local_path'])
        )
        instance.downloaded_at = data.get('downloaded_at', datetime.now().isoformat())
        return instance


class OBSPluginManager:
    """
    Manages OBS Studio plugins - downloading, tracking versions, and updates.
    """
    
    def __init__(self, config_manager: ConfigManager, obs_install_dir: Optional[Path] = None, github_token: Optional[str] = None):
        self.config_manager = config_manager
        self.obs_install_dir = obs_install_dir
        self.github_token = github_token
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"PluginManager initialized with obs_install_dir={obs_install_dir}")
        
        # Get download cache directory from config
        cache_dir = config_manager.get_download_cache_dir()
        self.cache_dir = Path(cache_dir)
        self.plugins_dir = self.cache_dir / "plugins"
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        
        # Version tracking file
        self.version_file = self.plugins_dir / "plugin_versions.json"
        self.downloaded_versions: Dict[str, PluginVersion] = {}
        self.load_version_tracking()
        
        # HTTP session for downloads
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'CGG-OBS-Installer/1.0.0'
        })
        
        # Add GitHub authentication if token is provided
        if self.github_token:
            self.session.headers['Authorization'] = f'token {self.github_token}'
            self.logger.info("Plugin manager initialized with GitHub authentication")
        else:
            self.logger.info("Plugin manager initialized without GitHub authentication")
        
        # File downloader
        self.downloader = FileDownloader()
    
    def load_plugins_config(self, plugins_json_path: Path) -> List[PluginInfo]:
        """
        Load plugin configuration from JSON file.
        
        Args:
            plugins_json_path: Path to plugins.json file
            
        Returns:
            List of PluginInfo objects
        """
        try:
            with open(plugins_json_path, 'r', encoding='utf-8') as f:
                plugins_data = json.load(f)
            
            plugins = []
            for name, config in plugins_data.items():
                if name == "OBS":  # Skip OBS itself, it's handled separately
                    continue
                
                filename = config.get('filename', '')
                release = config.get('release')  # Optional specific release
                
                if 'github' in config:
                    plugin = PluginInfo(name, filename, 'github', config['github'], release)
                elif 'obsproject' in config:
                    plugin = PluginInfo(name, filename, 'obsproject', config['obsproject'], release)
                else:
                    self.logger.warning(f"Plugin '{name}' has no valid source (github/obsproject)")
                    continue
                
                plugins.append(plugin)
            
            self.logger.info(f"Loaded {len(plugins)} plugin configurations")
            return plugins
            
        except Exception as e:
            self.logger.error(f"Failed to load plugins configuration: {e}")
            return []
    
    def load_version_tracking(self) -> None:
        """Load version tracking data from file."""
        try:
            if self.version_file.exists():
                with open(self.version_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.downloaded_versions = {
                    name: PluginVersion.from_dict(version_data)
                    for name, version_data in data.items()
                }
                
                self.logger.info(f"Loaded version tracking for {len(self.downloaded_versions)} plugins")
        except Exception as e:
            self.logger.error(f"Failed to load version tracking: {e}")
            self.downloaded_versions = {}
    
    def save_version_tracking(self) -> None:
        """Save version tracking data to file."""
        try:
            data = {
                name: version.to_dict()
                for name, version in self.downloaded_versions.items()
            }
            
            with open(self.version_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            self.logger.info("Version tracking data saved")
        except Exception as e:
            self.logger.error(f"Failed to save version tracking: {e}")
    
    def get_github_release_info(self, github_path: str, specific_release: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get release information from GitHub API.
        
        Args:
            github_path: Repository path (e.g., "owner/repo")
            specific_release: Specific release tag, or None for latest
            
        Returns:
            Release data dictionary or None if failed
        """
        try:
            if specific_release:
                url = f"https://api.github.com/repos/{github_path}/releases/tags/{specific_release}"
            else:
                url = f"https://api.github.com/repos/{github_path}/releases/latest"
            
            self.logger.info(f"Fetching GitHub release info from: {url}")
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            release_data = response.json()
            self.logger.info(f"Successfully fetched release info for {github_path}: {release_data.get('tag_name', 'unknown version')}")
            
            return release_data
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"HTTP error getting GitHub release info for {github_path}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error getting GitHub release info for {github_path}: {e}")
            return None
    
    def get_obsproject_download_url(self, obsproject_path: str, filename_pattern: str) -> Tuple[Optional[str], Optional[str], bool]:
        """
        Get actual download URL and filename for OBS Project resource by scraping the download page.
        
        Args:
            obsproject_path: OBS Project resource path (e.g., "plugin-name.1234")
            filename_pattern: Pattern to match filenames against
            
        Returns:
            Tuple of (download_url, filename, is_programdata_variant) or (None, None, False) if not found
        """
        if not HAS_BEAUTIFULSOUP:
            self.logger.error("BeautifulSoup4 is required for OBS Project downloads. Please install with: pip install beautifulsoup4")
            return None, None, False
            
        page_url = f"https://obsproject.com/forum/resources/{obsproject_path}/download"
        
        try:
            # Fetch the webpage
            response = requests.get(page_url)
            if response.status_code != 200:
                self.logger.error(f"Failed to fetch OBS Project page {page_url}: HTTP {response.status_code}")
                return None, None, False
            
            # Parse the HTML content
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Find all elements with class "contentRow-title" (these contain filenames)
            file_elements = soup.find_all(class_="contentRow-title")
            
            # Collect all matching files
            matching_files = []
            for file_element in file_elements:
                file_name = file_element.get_text().strip()
                self.logger.debug(f"Found file: {file_name}")
                
                # Check if filename matches the pattern
                if fnmatch(file_name, filename_pattern):
                    # Get the download link
                    download_link = file_element.find_previous("a", {"class": "button--icon--download"})
                    
                    if download_link is not None:
                        download_url = download_link["href"]
                        # Convert relative URL to absolute URL
                        if not download_url.startswith('http'):
                            download_url = requests.compat.urljoin(page_url, download_url)
                        
                        matching_files.append((download_url, file_name))
                        self.logger.debug(f"Found matching file: {file_name}")
            
            if not matching_files:
                available_files = [elem.get_text().strip() for elem in file_elements]
                self.logger.warning(f"No file matching pattern '{filename_pattern}' found. Available files: {available_files}")
                return None, None, False
            
            # Always prefer files WITHOUT "programdata" in the name
            for url, name in matching_files:
                if 'programdata' not in name.lower():
                    self.logger.info(f"Selected standard variant: {name}")
                    return url, name, False
            
            # If only programdata versions available, use the first match
            url, name = matching_files[0]
            is_programdata = 'programdata' in name.lower()
            if is_programdata:
                self.logger.warning(f"Only ProgramData variant found, using: {name}")
            return url, name, is_programdata
            
        except Exception as e:
            self.logger.error(f"Error scraping OBS Project page {page_url}: {e}")
            return None, None, False
    
    def find_matching_asset(self, assets: List[Dict[str, Any]], filename_pattern: str) -> Optional[Dict[str, Any]]:
        """
        Find asset that matches the filename pattern.
        
        Args:
            assets: List of GitHub release assets
            filename_pattern: Pattern to match (supports wildcards with *)
            
        Returns:
            Matching asset or None
        """
        # Log available assets for debugging
        asset_names = [asset['name'] for asset in assets]
        self.logger.info(f"Available assets: {asset_names}")
        self.logger.info(f"Looking for pattern: {filename_pattern}")
        
        # Convert filename pattern to regex
        pattern = filename_pattern.replace('*', '.*')
        pattern = f"^{pattern}$"
        
        try:
            regex = re.compile(pattern, re.IGNORECASE)
            for asset in assets:
                if regex.match(asset['name']):
                    self.logger.info(f"Found matching asset: {asset['name']}")
                    return asset
            
            self.logger.warning(f"No assets matched pattern '{filename_pattern}' from {len(assets)} available assets")
            
            # Fallback: Try to find any Windows x64 asset
            self.logger.info("Attempting fallback matching for Windows x64 assets...")
            for asset in assets:
                name_lower = asset['name'].lower()
                if ('windows' in name_lower or 'win' in name_lower) and 'x64' in name_lower:
                    if name_lower.endswith('.zip') or name_lower.endswith('.7z'):
                        self.logger.info(f"Found fallback Windows x64 asset: {asset['name']}")
                        return asset
            
            # Final fallback: Any .zip or .7z file
            for asset in assets:
                if asset['name'].lower().endswith(('.zip', '.7z')):
                    self.logger.info(f"Found fallback archive asset: {asset['name']}")
                    return asset
                    
        except re.error as e:
            self.logger.error(f"Invalid filename pattern '{filename_pattern}': {e}")
        
        return None
    
    def needs_update(self, plugin: PluginInfo, latest_version: str, latest_date: str) -> bool:
        """
        Check if plugin needs to be updated.
        
        Args:
            plugin: Plugin information
            latest_version: Latest available version
            latest_date: Latest release date
            
        Returns:
            True if plugin needs update
        """
        if plugin.name not in self.downloaded_versions:
            return True  # Not downloaded yet
        
        current = self.downloaded_versions[plugin.name]
        
        # Check if local file still exists
        if not current.local_path.exists():
            self.logger.info(f"Plugin {plugin.name} file missing, needs re-download")
            return True
        
        # Compare versions if available
        if latest_version and current.version != latest_version:
            self.logger.info(f"Plugin {plugin.name} version changed: {current.version} -> {latest_version}")
            return True
        
        # Compare dates if versions are the same or not available
        if latest_date and current.release_date != latest_date:
            self.logger.info(f"Plugin {plugin.name} date changed: {current.release_date} -> {latest_date}")
            return True
        
        self.logger.info(f"Plugin {plugin.name} is up to date")
        return False
    
    def download_plugin(self, plugin: PluginInfo, download_url: str, filename: str, 
                       version: str, release_date: str, is_programdata_variant: bool = False) -> Optional[Path]:
        """
        Download a plugin file.
        
        Args:
            plugin: Plugin information
            download_url: URL to download from
            filename: Local filename
            version: Plugin version
            release_date: Release date
            
        Returns:
            Path to downloaded file or None if failed
        """
        try:
            local_path = self.plugins_dir / filename
            
            # Create progress callback
            def progress_callback(progress: DownloadProgress):
                try:
                    downloaded_mb = progress.downloaded_bytes / 1024 / 1024
                    total_mb = progress.total_bytes / 1024 / 1024 if progress.total_bytes > 0 else 0
                    if total_mb > 0:
                        self.logger.info(f"Downloading {plugin.name}: {progress.percentage:.1f}% "
                                       f"({downloaded_mb:.1f}/{total_mb:.1f} MB)")
                    else:
                        self.logger.info(f"Downloading {plugin.name}: {downloaded_mb:.1f} MB downloaded")
                except Exception as e:
                    self.logger.warning(f"Error in progress callback for {plugin.name}: {e}")
            
            # Download the file using the correct method signature
            result = self.downloader.download_file(
                url=download_url,
                target_path=self.plugins_dir,  # Directory path
                filename=filename,             # Just the filename
                progress_callback=progress_callback
            )
            
            if result.success and result.file_path:
                # Update version tracking
                plugin_version = PluginVersion(
                    name=plugin.name,
                    version=version,
                    release_date=release_date,
                    download_url=download_url,
                    local_path=result.file_path
                )
                
                self.downloaded_versions[plugin.name] = plugin_version
                self.save_version_tracking()
                
                self.logger.info(f"Successfully downloaded {plugin.name} to {result.file_path}")
                
                # Extract the plugin if OBS install directory is available
                if self.obs_install_dir:
                    self.extract_plugin(result.file_path, plugin.name, is_programdata_variant)
                
                return result.file_path
            else:
                error_msg = result.error_message or "Unknown download error"
                self.logger.error(f"Failed to download {plugin.name}: {error_msg}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error downloading {plugin.name}: {e}")
            return None
    
    def extract_plugin(self, archive_path: Path, plugin_name: str, is_programdata_variant: bool = False) -> bool:
        """
        Extract plugin archive to OBS installation directory.
        
        Args:
            archive_path: Path to the downloaded archive
            plugin_name: Name of the plugin for logging
            is_programdata_variant: Whether this is a ProgramData-specific plugin variant (for logging only)
            
        Returns:
            True if extraction successful, False otherwise
        """
        # Always install to OBS directory
        if not self.obs_install_dir:
            self.logger.warning(f"No OBS installation directory set, skipping extraction of {plugin_name}")
            return False
            
        target_dir = self.obs_install_dir
        self.logger.info(f"Extracting {plugin_name} to OBS installation directory: {target_dir}")
            
        if not archive_path.exists():
            self.logger.error(f"Archive file not found: {archive_path}")
            return False
            
        try:
            self.logger.info(f"Extracting {plugin_name} to {target_dir}")
            
            # Get file extension to determine extraction method
            file_ext = archive_path.suffix.lower()
            
            if file_ext == '.zip':
                return self._extract_zip(archive_path, target_dir, plugin_name)
            elif file_ext == '.7z':
                return self._extract_7z(archive_path, target_dir, plugin_name)
            else:
                self.logger.error(f"Unsupported archive format: {file_ext}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error extracting {plugin_name}: {e}")
            return False
    
    def _extract_zip(self, zip_path: Path, extract_to: Path, plugin_name: str) -> bool:
        """Extract ZIP file to target directory."""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_file:
                # Extract all files, overwriting existing files
                zip_file.extractall(extract_to)
                
            self.logger.info(f"Successfully extracted ZIP {plugin_name} to {extract_to}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error extracting ZIP {plugin_name}: {e}")
            return False
    
    def _extract_7z(self, archive_path: Path, extract_to: Path, plugin_name: str) -> bool:
        """Extract 7z file to target directory."""
        if not HAS_PY7ZR:
            self.logger.error("py7zr is required for 7z extraction. Please install with: pip install py7zr")
            return False
            
        try:
            with py7zr.SevenZipFile(archive_path, mode='r') as archive:
                # Extract all files, overwriting existing files
                archive.extractall(path=extract_to)
                
            self.logger.info(f"Successfully extracted 7z {plugin_name} to {extract_to}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error extracting 7z {plugin_name}: {e}")
            return False
    
    def download_github_plugin(self, plugin: PluginInfo) -> Optional[Path]:
        """Download plugin from GitHub."""
        release_info = self.get_github_release_info(plugin.source_path, plugin.release)
        if not release_info:
            return None
        
        # Find matching asset
        assets = release_info.get('assets', [])
        matching_asset = self.find_matching_asset(assets, plugin.filename_pattern)
        
        if not matching_asset:
            self.logger.error(f"No matching asset found for {plugin.name} pattern: {plugin.filename_pattern}")
            return None
        
        version = release_info.get('tag_name', 'unknown')
        release_date = release_info.get('published_at', 'unknown')
        download_url = matching_asset['browser_download_url']
        filename = matching_asset['name']
        
        # Check if update is needed
        if not self.needs_update(plugin, version, release_date):
            return self.downloaded_versions[plugin.name].local_path
        
        return self.download_plugin(plugin, download_url, filename, version, release_date)
    
    def download_obsproject_plugin(self, plugin: PluginInfo) -> Optional[Path]:
        """Download plugin from OBS Project."""
        # Get the actual download URL and filename by scraping the page
        download_url, actual_filename, is_programdata_variant = self.get_obsproject_download_url(
            plugin.source_path, plugin.filename_pattern
        )
        
        if not download_url or not actual_filename:
            self.logger.error(f"Could not find download URL for OBS Project plugin {plugin.name}")
            return None
        
        # Use the actual filename from the page
        filename = actual_filename
        
        # Try to get version info from the path (resource ID)
        version = plugin.source_path.split('.')[-1] if '.' in plugin.source_path else 'unknown'
        release_date = datetime.now().strftime('%Y-%m-%d')  # Use current date as fallback
        
        # Check if we need to update (simplified for OBS Project)
        if plugin.name in self.downloaded_versions:
            current = self.downloaded_versions[plugin.name]
            if current.local_path.exists():
                # For OBS Project, we'll re-download if file is older than 1 day
                # This is a simple heuristic since we don't have good version info
                file_age = datetime.now() - datetime.fromisoformat(current.downloaded_at.replace('Z', '+00:00').replace('+00:00', ''))
                if file_age.days < 1:
                    self.logger.info(f"OBS Project plugin {plugin.name} was downloaded recently, skipping")
                    return current.local_path
        
        return self.download_plugin(plugin, download_url, filename, version, release_date, is_programdata_variant)
    
    def download_all_plugins(self, plugins_json_path: Path, 
                           progress_callback: Optional[callable] = None) -> Tuple[int, int, List[str]]:
        """
        Download all plugins from the configuration.
        
        Args:
            plugins_json_path: Path to plugins.json
            progress_callback: Optional callback for progress updates
            
        Returns:
            Tuple of (successful_downloads, total_plugins, error_messages)
        """
        plugins = self.load_plugins_config(plugins_json_path)
        if not plugins:
            return 0, 0, ["No plugins found in configuration"]
        
        successful = 0
        errors = []
        total = len(plugins)
        
        for i, plugin in enumerate(plugins):
            try:
                if progress_callback:
                    action = "Downloading and extracting" if self.obs_install_dir else "Downloading"
                    progress_callback(i + 1, total, f"{action} {plugin.name}...")
                
                self.logger.info(f"Processing plugin: {plugin.name}")
                
                if plugin.source_type == 'github':
                    result = self.download_github_plugin(plugin)
                elif plugin.source_type == 'obsproject':
                    result = self.download_obsproject_plugin(plugin)
                else:
                    errors.append(f"Unknown source type for {plugin.name}: {plugin.source_type}")
                    continue
                
                if result:
                    successful += 1
                    self.logger.info(f"Successfully processed {plugin.name}")
                else:
                    errors.append(f"Failed to download {plugin.name}")
                    
            except Exception as e:
                error_msg = f"Error processing {plugin.name}: {str(e)}"
                errors.append(error_msg)
                self.logger.error(error_msg)
        
        self.logger.info(f"Plugin download completed: {successful}/{total} successful")
        return successful, total, errors
    
    def get_downloaded_plugins(self) -> List[PluginVersion]:
        """Get list of all downloaded plugins."""
        return list(self.downloaded_versions.values())
    
    def cleanup_old_plugins(self, keep_days: int = 30) -> None:
        """
        Clean up old plugin files.
        
        Args:
            keep_days: Number of days to keep old versions
        """
        try:
            cutoff_date = datetime.now().timestamp() - (keep_days * 24 * 60 * 60)
            
            for plugin_file in self.plugins_dir.glob("*"):
                if plugin_file.is_file() and plugin_file.name != "plugin_versions.json":
                    if plugin_file.stat().st_mtime < cutoff_date:
                        plugin_file.unlink()
                        self.logger.info(f"Cleaned up old plugin file: {plugin_file.name}")
                        
        except Exception as e:
            self.logger.error(f"Error during plugin cleanup: {e}")