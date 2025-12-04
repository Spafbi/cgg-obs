"""
GitHub API Client for OBS Studio Releases

Handles interaction with GitHub's REST API to:
- Fetch latest OBS Studio release information
- Filter out pre-release versions
- Get download URLs for Windows x64 builds
- Cache release information to minimize API calls
"""

import json
import logging
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path

import requests
from ..utils.downloader import FileDownloader


@dataclass
class ReleaseAsset:
    """
    Information about a release asset (downloadable file).
    
    Attributes:
        name: Asset filename
        download_url: Direct download URL
        size: File size in bytes
        content_type: MIME type of the file
        created_at: Creation timestamp
    """
    name: str
    download_url: str
    size: int
    content_type: str
    created_at: str


@dataclass
class Release:
    """
    Information about a GitHub release.
    
    Attributes:
        tag_name: Git tag name (version)
        name: Release name/title
        published_at: Publication timestamp
        prerelease: Whether this is a pre-release
        assets: List of downloadable assets
        body: Release description/notes
    """
    tag_name: str
    name: str
    published_at: str
    prerelease: bool
    assets: List[ReleaseAsset]
    body: str


class GitHubAPIClient:
    """
    Client for interacting with GitHub's REST API to get OBS Studio releases.
    
    Features:
    - Automatic rate limiting respect
    - Response caching to minimize API calls
    - Pre-release filtering
    - Windows x64 asset filtering
    """
    
    def __init__(self, cache_duration: int = 300, github_token: Optional[str] = None):
        """
        Initialize the GitHub API client.
        
        Args:
            cache_duration: How long to cache responses in seconds (default: 5 minutes)
            github_token: Optional GitHub Personal Access Token for authenticated requests
        """
        self.logger = logging.getLogger(__name__)
        self.base_url = "https://api.github.com"
        self.repo_owner = "obsproject"
        self.repo_name = "obs-studio"
        self.cache_duration = cache_duration
        self.github_token = github_token
        
        # Cache for API responses
        self._cache: Dict[str, Dict[str, Any]] = {}
        
        # Setup session with appropriate headers
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'OBS-Installer/1.0 (Windows)'
        })
        
        # Add authentication if token is provided
        if self.github_token:
            self.session.headers['Authorization'] = f'token {self.github_token}'
            self.logger.info("GitHub API client initialized with authentication token")
            # Authenticated requests have higher rate limits (5000/hour vs 60/hour)
            self.rate_limit_remaining = 5000
        else:
            self.logger.info("GitHub API client initialized without authentication (rate limited)")
            # Rate limiting tracking for unauthenticated requests
            self.rate_limit_remaining = 60  # GitHub's default for unauthenticated requests
            
        self.rate_limit_reset = time.time() + 3600
    
    def set_github_token(self, token: Optional[str]) -> bool:
        """
        Set or update the GitHub Personal Access Token.
        
        Args:
            token: GitHub Personal Access Token, or None to remove authentication
            
        Returns:
            bool: True if token was set successfully, False if invalid
        """
        if token and token.strip():
            # Validate token format (GitHub tokens start with specific prefixes)
            token = token.strip()
            if not (token.startswith('ghp_') or token.startswith('github_pat_') or 
                   token.startswith('gho_') or token.startswith('ghu_') or 
                   token.startswith('ghs_') or token.startswith('ghr_')):
                self.logger.warning("GitHub token does not match expected format")
                # Don't reject it completely as GitHub may change formats
            
            self.github_token = token
            self.session.headers['Authorization'] = f'token {token}'
            self.rate_limit_remaining = 5000  # Higher limit for authenticated requests
            self.logger.info("GitHub authentication token updated")
            return True
        else:
            # Remove authentication
            self.github_token = None
            if 'Authorization' in self.session.headers:
                del self.session.headers['Authorization']
            self.rate_limit_remaining = 60  # Lower limit for unauthenticated requests
            self.logger.info("GitHub authentication removed")
            return True
    
    def validate_token(self) -> tuple[bool, str]:
        """
        Validate the current GitHub token by making a test API request.
        
        Returns:
            tuple[bool, str]: (is_valid, error_message)
        """
        if not self.github_token:
            return True, "No token configured (using unauthenticated requests)"
        
        try:
            # Test the token with a simple API call
            response = self.session.get(f"{self.base_url}/user", timeout=10)
            
            if response.status_code == 200:
                user_data = response.json()
                username = user_data.get('login', 'unknown')
                self.logger.info(f"GitHub token validated successfully for user: {username}")
                return True, f"Token valid for user: {username}"
            elif response.status_code == 401:
                self.logger.error("GitHub token is invalid or expired")
                return False, "Invalid or expired token"
            elif response.status_code == 403:
                self.logger.error("GitHub token lacks required permissions")
                return False, "Token lacks required permissions"
            else:
                self.logger.error(f"Unexpected response validating token: {response.status_code}")
                return False, f"Validation failed with status {response.status_code}"
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error validating GitHub token: {e}")
            return False, f"Network error: {str(e)}"
    
    def get_latest_release(self, include_prerelease: bool = False) -> Optional[Release]:
        """
        Get the latest OBS Studio release.
        
        Args:
            include_prerelease: Whether to include pre-release versions
            
        Returns:
            Release: Latest release information, or None if error
        """
        self.logger.info("Fetching latest OBS Studio release information")
        
        try:
            # Check cache first
            cache_key = f"latest_release_{include_prerelease}"
            if self._is_cache_valid(cache_key):
                self.logger.debug("Using cached release information")
                return self._parse_release_data(self._cache[cache_key]['data'])
            
            # If we want stable releases only, use the /latest endpoint
            if not include_prerelease:
                endpoint = f"/repos/{self.repo_owner}/{self.repo_name}/releases/latest"
                release_data = self._make_api_request(endpoint)
                if release_data:
                    # Cache the response
                    self._cache[cache_key] = {
                        'data': release_data,
                        'timestamp': time.time()
                    }
                    return self._parse_release_data(release_data)
            else:
                # If we want to include pre-releases, get all releases and find the latest
                releases = self.get_releases(limit=10)  # Get recent releases
                if releases:
                    # Return the first (most recent) release
                    latest = releases[0]
                    self._cache[cache_key] = {
                        'data': latest.__dict__,
                        'timestamp': time.time()
                    }
                    return latest
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching latest release: {e}")
            return None
    
    def get_releases(self, limit: int = 30, include_prerelease: bool = False) -> List[Release]:
        """
        Get a list of OBS Studio releases.
        
        Args:
            limit: Maximum number of releases to return
            include_prerelease: Whether to include pre-release versions
            
        Returns:
            List[Release]: List of releases, newest first
        """
        self.logger.info(f"Fetching OBS Studio releases (limit: {limit})")
        
        try:
            # Check cache first
            cache_key = f"releases_{limit}_{include_prerelease}"
            if self._is_cache_valid(cache_key):
                self.logger.debug("Using cached releases information")
                cached_data = self._cache[cache_key]['data']
                return [self._parse_release_data(r) for r in cached_data]
            
            endpoint = f"/repos/{self.repo_owner}/{self.repo_name}/releases"
            params = {'per_page': min(limit, 100)}  # GitHub's max per_page is 100
            
            releases_data = self._make_api_request(endpoint, params)
            if not releases_data:
                return []
            
            # Parse and filter releases
            releases = []
            for release_data in releases_data:
                release = self._parse_release_data(release_data)
                
                # Filter pre-releases if not wanted
                if not include_prerelease and release.prerelease:
                    continue
                
                releases.append(release)
                
                # Stop if we've reached the limit
                if len(releases) >= limit:
                    break
            
            # Cache the response
            self._cache[cache_key] = {
                'data': [r.__dict__ for r in releases],
                'timestamp': time.time()
            }
            
            self.logger.info(f"Found {len(releases)} releases")
            return releases
            
        except Exception as e:
            self.logger.error(f"Error fetching releases: {e}")
            return []
    
    def get_windows_x64_asset(self, release: Release) -> Optional[ReleaseAsset]:
        """
        Find the Windows x64 ZIP asset in a release.
        
        Args:
            release: Release to search for Windows x64 asset
            
        Returns:
            ReleaseAsset: Windows x64 asset, or None if not found
        """
        # Look for Windows x64 ZIP file
        windows_patterns = [
            'windows-x64.zip',
            'windows_x64.zip', 
            'win64.zip',
            'x64.zip'
        ]
        
        for asset in release.assets:
            asset_name_lower = asset.name.lower()
            
            # Must be a ZIP file
            if not asset_name_lower.endswith('.zip'):
                continue
            
            # Must contain Windows x64 indicators
            if any(pattern in asset_name_lower for pattern in windows_patterns):
                self.logger.info(f"Found Windows x64 asset: {asset.name}")
                return asset
        
        # Fallback: look for any ZIP that seems Windows-related
        for asset in release.assets:
            asset_name_lower = asset.name.lower()
            if (asset_name_lower.endswith('.zip') and 
                ('windows' in asset_name_lower or 'win' in asset_name_lower)):
                self.logger.warning(
                    f"Using fallback Windows asset: {asset.name} "
                    "(could not find specific x64 version)"
                )
                return asset
        
        self.logger.error(f"No Windows x64 asset found in release {release.tag_name}")
        return None
    
    def check_for_newer_version(self, current_version: str, 
                               include_prerelease: bool = False) -> Optional[Release]:
        """
        Check if there's a newer version available than the current one.
        
        Args:
            current_version: Current version string (e.g., "30.0.2")
            include_prerelease: Whether to consider pre-releases
            
        Returns:
            Release: Newer release if available, None otherwise
        """
        self.logger.info(f"Checking for newer version than {current_version}")
        
        latest_release = self.get_latest_release(include_prerelease)
        if not latest_release:
            return None
        
        # Compare versions (simple string comparison for now)
        # This works for semantic versioning like "30.0.2"
        latest_version = latest_release.tag_name.lstrip('v')  # Remove 'v' prefix if present
        
        if self._compare_versions(latest_version, current_version) > 0:
            self.logger.info(f"Newer version available: {latest_version}")
            return latest_release
        else:
            self.logger.info("No newer version available")
            return None
    
    def _make_api_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Any]:
        """
        Make a request to the GitHub API with rate limiting and error handling.
        
        Args:
            endpoint: API endpoint to request
            params: Query parameters
            
        Returns:
            API response data or None if error
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            # Check rate limiting
            if self.rate_limit_remaining <= 1 and time.time() < self.rate_limit_reset:
                wait_time = self.rate_limit_reset - time.time()
                self.logger.warning(f"Rate limit reached, waiting {wait_time:.1f}s")
                time.sleep(wait_time)
            
            response = self.session.get(url, params=params, timeout=30)
            
            # Update rate limiting info
            if 'X-RateLimit-Remaining' in response.headers:
                self.rate_limit_remaining = int(response.headers['X-RateLimit-Remaining'])
            if 'X-RateLimit-Reset' in response.headers:
                self.rate_limit_reset = int(response.headers['X-RateLimit-Reset'])
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed for {url}: {e}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON response from {url}: {e}")
            return None
    
    def _parse_release_data(self, data: Dict[str, Any]) -> Release:
        """
        Parse release data from GitHub API response.
        
        Args:
            data: Raw release data from API
            
        Returns:
            Release: Parsed release object
        """
        # Parse assets
        assets = []
        for asset_data in data.get('assets', []):
            asset = ReleaseAsset(
                name=asset_data['name'],
                download_url=asset_data['browser_download_url'],
                size=asset_data['size'],
                content_type=asset_data.get('content_type', 'unknown'),
                created_at=asset_data['created_at']
            )
            assets.append(asset)
        
        return Release(
            tag_name=data['tag_name'],
            name=data['name'],
            published_at=data['published_at'],
            prerelease=data['prerelease'],
            assets=assets,
            body=data.get('body', '')
        )
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """
        Check if cached data is still valid.
        
        Args:
            cache_key: Key to check in cache
            
        Returns:
            bool: True if cache is valid
        """
        if cache_key not in self._cache:
            return False
        
        cache_age = time.time() - self._cache[cache_key]['timestamp']
        return cache_age < self.cache_duration
    
    def _compare_versions(self, version1: str, version2: str) -> int:
        """
        Compare two version strings.
        
        Args:
            version1: First version to compare
            version2: Second version to compare
            
        Returns:
            int: 1 if version1 > version2, -1 if version1 < version2, 0 if equal
        """
        try:
            # Split versions into parts and convert to integers
            parts1 = [int(x) for x in version1.split('.')]
            parts2 = [int(x) for x in version2.split('.')]
            
            # Pad shorter version with zeros
            max_len = max(len(parts1), len(parts2))
            parts1.extend([0] * (max_len - len(parts1)))
            parts2.extend([0] * (max_len - len(parts2)))
            
            # Compare parts
            for p1, p2 in zip(parts1, parts2):
                if p1 > p2:
                    return 1
                elif p1 < p2:
                    return -1
            
            return 0
            
        except ValueError:
            # Fallback to string comparison
            self.logger.warning(f"Could not parse versions numerically: {version1}, {version2}")
            if version1 > version2:
                return 1
            elif version1 < version2:
                return -1
            else:
                return 0
    
    def clear_cache(self) -> None:
        """Clear the API response cache."""
        self._cache.clear()
        self.logger.info("API cache cleared")
    
    def __del__(self):
        """Cleanup when client is destroyed."""
        if hasattr(self, 'session'):
            self.session.close()