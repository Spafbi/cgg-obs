"""
Generic File Downloader for OBS Installer

Provides a robust, reusable file download system with:
- Progress tracking and callbacks
- Resume capability for interrupted downloads
- Comprehensive error handling
- Configurable timeouts and retries
- File integrity verification
"""

import os
import requests
import hashlib
from pathlib import Path
from typing import Optional, Callable, Dict, Any, Tuple
from dataclasses import dataclass
import logging
import time
from urllib.parse import urlparse


@dataclass
class DownloadResult:
    """
    Container for download operation results.
    
    Attributes:
        success: Whether the download completed successfully
        file_path: Path to the downloaded file
        file_size: Size of the downloaded file in bytes
        download_time: Time taken for download in seconds
        error_message: Error description if download failed
        http_status: HTTP status code from the request
    """
    success: bool
    file_path: Optional[Path] = None
    file_size: int = 0
    download_time: float = 0.0
    error_message: Optional[str] = None
    http_status: Optional[int] = None


@dataclass
class DownloadProgress:
    """
    Container for download progress information.
    
    Attributes:
        downloaded_bytes: Number of bytes downloaded so far
        total_bytes: Total file size in bytes (if known)
        percentage: Download completion percentage (0-100)
        speed_bps: Current download speed in bytes per second
        eta_seconds: Estimated time remaining in seconds
    """
    downloaded_bytes: int
    total_bytes: int
    percentage: float
    speed_bps: float
    eta_seconds: float


class FileDownloader:
    """
    A robust file downloader with progress tracking and error handling.
    
    Features:
    - Resume interrupted downloads
    - Progress callbacks for UI integration
    - Configurable retry logic
    - File integrity verification
    - Comprehensive error handling
    """
    
    def __init__(self, 
                 chunk_size: int = 8192,
                 timeout: int = 30,
                 max_retries: int = 3,
                 retry_delay: float = 1.0):
        """
        Initialize the file downloader.
        
        Args:
            chunk_size: Size of chunks to download at a time (bytes)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.chunk_size = chunk_size
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = logging.getLogger(__name__)
        
        # Session for connection pooling and header persistence
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'OBS-Installer/1.0 (Windows)'
        })
    
    def download_file(self,
                     url: str,
                     target_path: Path,
                     filename: Optional[str] = None,
                     progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
                     resume: bool = True,
                     verify_ssl: bool = True) -> DownloadResult:
        """
        Download a file from URL to target location.
        
        Args:
            url: URL to download from
            target_path: Directory path where file will be saved
            filename: Specific filename to use (if None, extracted from URL)
            progress_callback: Function to call with progress updates
            resume: Whether to resume interrupted downloads
            verify_ssl: Whether to verify SSL certificates
            
        Returns:
            DownloadResult: Details about the download operation
        """
        start_time = time.time()
        
        try:
            # Ensure target directory exists
            target_path.mkdir(parents=True, exist_ok=True)
            
            # Determine filename
            if filename is None:
                filename = self._extract_filename_from_url(url)
            
            file_path = target_path / filename
            
            self.logger.info(f"Starting download from {url} to {file_path}")
            
            # Check if file already exists and get existing size
            existing_size = 0
            if resume and file_path.exists():
                existing_size = file_path.stat().st_size
                self.logger.info(f"Found existing file with {existing_size} bytes")
            
            # Attempt download with retries
            for attempt in range(1, self.max_retries + 1):
                try:
                    result = self._attempt_download(
                        url, file_path, existing_size, progress_callback, verify_ssl
                    )
                    
                    if result.success:
                        result.download_time = time.time() - start_time
                        self.logger.info(
                            f"Download completed in {result.download_time:.2f}s"
                        )
                        return result
                    
                    # If not the last attempt, log and retry
                    if attempt < self.max_retries:
                        self.logger.warning(
                            f"Download attempt {attempt} failed: {result.error_message}. "
                            f"Retrying in {self.retry_delay}s..."
                        )
                        time.sleep(self.retry_delay)
                    else:
                        # Last attempt failed
                        result.download_time = time.time() - start_time
                        return result
                        
                except Exception as e:
                    error_msg = f"Download attempt {attempt} raised exception: {str(e)}"
                    self.logger.error(error_msg)
                    
                    if attempt == self.max_retries:
                        return DownloadResult(
                            success=False,
                            file_path=file_path,
                            download_time=time.time() - start_time,
                            error_message=error_msg
                        )
                    
                    time.sleep(self.retry_delay)
            
        except Exception as e:
            error_msg = f"Download setup failed: {str(e)}"
            self.logger.error(error_msg)
            return DownloadResult(
                success=False,
                download_time=time.time() - start_time,
                error_message=error_msg
            )
    
    def _attempt_download(self,
                         url: str,
                         file_path: Path,
                         existing_size: int,
                         progress_callback: Optional[Callable[[DownloadProgress], None]],
                         verify_ssl: bool) -> DownloadResult:
        """
        Attempt a single download operation.
        
        Args:
            url: URL to download from
            file_path: Path where file will be saved
            existing_size: Size of existing partial file (for resume)
            progress_callback: Progress callback function
            verify_ssl: Whether to verify SSL certificates
            
        Returns:
            DownloadResult: Result of the download attempt
        """
        headers = {}
        mode = 'wb'
        
        # Set up resume headers if needed
        if existing_size > 0:
            headers['Range'] = f'bytes={existing_size}-'
            mode = 'ab'
            self.logger.info(f"Resuming download from byte {existing_size}")
        
        try:
            # Make the request
            response = self.session.get(
                url,
                headers=headers,
                stream=True,
                timeout=self.timeout,
                verify=verify_ssl
            )
            
            # Check for successful response
            if response.status_code not in [200, 206]:  # 206 for partial content
                return DownloadResult(
                    success=False,
                    file_path=file_path,
                    http_status=response.status_code,
                    error_message=f"HTTP {response.status_code}: {response.reason}"
                )
            
            # Get total file size
            content_length = response.headers.get('content-length')
            if content_length:
                total_size = int(content_length) + existing_size
            else:
                total_size = 0  # Unknown size
            
            self.logger.info(f"Total file size: {total_size} bytes")
            
            # Download the file
            downloaded_size = existing_size
            last_progress_time = time.time()
            last_downloaded_size = downloaded_size
            
            with open(file_path, mode) as f:
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    if chunk:  # Filter out keep-alive chunks
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # Update progress callback
                        if progress_callback:
                            current_time = time.time()
                            time_diff = current_time - last_progress_time
                            
                            # Update progress every 0.1 seconds to avoid UI spam
                            if time_diff >= 0.1:
                                size_diff = downloaded_size - last_downloaded_size
                                speed_bps = size_diff / time_diff if time_diff > 0 else 0
                                
                                percentage = 0.0
                                eta_seconds = 0.0
                                
                                if total_size > 0:
                                    percentage = (downloaded_size / total_size) * 100
                                    remaining_bytes = total_size - downloaded_size
                                    eta_seconds = remaining_bytes / speed_bps if speed_bps > 0 else 0
                                
                                progress = DownloadProgress(
                                    downloaded_bytes=downloaded_size,
                                    total_bytes=total_size,
                                    percentage=percentage,
                                    speed_bps=speed_bps,
                                    eta_seconds=eta_seconds
                                )
                                
                                progress_callback(progress)
                                
                                last_progress_time = current_time
                                last_downloaded_size = downloaded_size
            
            # Final progress update
            if progress_callback and total_size > 0:
                progress = DownloadProgress(
                    downloaded_bytes=downloaded_size,
                    total_bytes=total_size,
                    percentage=100.0,
                    speed_bps=0.0,
                    eta_seconds=0.0
                )
                progress_callback(progress)
            
            return DownloadResult(
                success=True,
                file_path=file_path,
                file_size=downloaded_size,
                http_status=response.status_code
            )
            
        except requests.exceptions.Timeout:
            return DownloadResult(
                success=False,
                file_path=file_path,
                error_message="Download timed out"
            )
        except requests.exceptions.ConnectionError:
            return DownloadResult(
                success=False,
                file_path=file_path,
                error_message="Connection error"
            )
        except requests.exceptions.RequestException as e:
            return DownloadResult(
                success=False,
                file_path=file_path,
                error_message=f"Request error: {str(e)}"
            )
        except OSError as e:
            return DownloadResult(
                success=False,
                file_path=file_path,
                error_message=f"File system error: {str(e)}"
            )
    
    def _extract_filename_from_url(self, url: str) -> str:
        """
        Extract filename from URL.
        
        Args:
            url: URL to extract filename from
            
        Returns:
            str: Extracted filename
        """
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)
        
        # If no filename in URL, create a generic one
        if not filename or '.' not in filename:
            filename = f"download_{int(time.time())}.bin"
        
        return filename
    
    def get_file_info(self, url: str, verify_ssl: bool = True) -> Dict[str, Any]:
        """
        Get information about a file without downloading it.
        
        Args:
            url: URL to get information about
            verify_ssl: Whether to verify SSL certificates
            
        Returns:
            dict: File information including size, type, last-modified
        """
        try:
            response = self.session.head(url, timeout=self.timeout, verify=verify_ssl)
            
            if response.status_code != 200:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.reason}"
                }
            
            headers = response.headers
            return {
                'success': True,
                'size': int(headers.get('content-length', 0)),
                'content_type': headers.get('content-type', 'unknown'),
                'last_modified': headers.get('last-modified'),
                'filename': self._extract_filename_from_url(url),
                'supports_resume': 'accept-ranges' in headers
            }
            
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f"Request error: {str(e)}"
            }
    
    def verify_file_integrity(self, file_path: Path, expected_hash: str, 
                            hash_algorithm: str = 'sha256') -> bool:
        """
        Verify file integrity using hash comparison.
        
        Args:
            file_path: Path to file to verify
            expected_hash: Expected hash value
            hash_algorithm: Hash algorithm to use (md5, sha1, sha256, etc.)
            
        Returns:
            bool: True if file integrity is verified
        """
        try:
            if not file_path.exists():
                return False
            
            hasher = hashlib.new(hash_algorithm)
            
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(self.chunk_size), b""):
                    hasher.update(chunk)
            
            calculated_hash = hasher.hexdigest().lower()
            expected_hash = expected_hash.lower()
            
            is_valid = calculated_hash == expected_hash
            
            if is_valid:
                self.logger.info(f"File integrity verified: {file_path}")
            else:
                self.logger.error(
                    f"File integrity check failed for {file_path}. "
                    f"Expected: {expected_hash}, Got: {calculated_hash}"
                )
            
            return is_valid
            
        except Exception as e:
            self.logger.error(f"Error verifying file integrity: {e}")
            return False
    
    def cleanup_partial_download(self, file_path: Path) -> bool:
        """
        Clean up a partial download file.
        
        Args:
            file_path: Path to the partial file to clean up
            
        Returns:
            bool: True if cleanup was successful
        """
        try:
            if file_path.exists():
                file_path.unlink()
                self.logger.info(f"Cleaned up partial download: {file_path}")
                return True
            return True
        except OSError as e:
            self.logger.error(f"Failed to cleanup partial download {file_path}: {e}")
            return False
    
    def __del__(self):
        """Cleanup when downloader is destroyed."""
        if hasattr(self, 'session'):
            self.session.close()