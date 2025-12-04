"""
ZIP Extraction Utilities for OBS Installer

Provides robust ZIP file extraction with:
- Progress tracking for UI integration
- Comprehensive error handling
- File integrity verification
- Selective extraction capabilities
- Cross-platform path handling
"""

import os
import zipfile
import shutil
from pathlib import Path
from typing import Optional, Callable, List, Dict, Any
from dataclasses import dataclass
import logging
import time


@dataclass
class ExtractionProgress:
    """
    Container for extraction progress information.
    
    Attributes:
        current_file: Name of file currently being extracted
        files_extracted: Number of files extracted so far
        total_files: Total number of files to extract
        bytes_extracted: Number of bytes extracted so far
        total_bytes: Total size of all files to extract
        percentage: Extraction completion percentage (0-100)
    """
    current_file: str
    files_extracted: int
    total_files: int
    bytes_extracted: int
    total_bytes: int
    percentage: float


@dataclass
class ExtractionResult:
    """
    Container for extraction operation results.
    
    Attributes:
        success: Whether the extraction completed successfully
        extracted_path: Path where files were extracted
        files_extracted: Number of files successfully extracted
        total_size: Total size of extracted files in bytes
        extraction_time: Time taken for extraction in seconds
        error_message: Error description if extraction failed
    """
    success: bool
    extracted_path: Optional[Path] = None
    files_extracted: int = 0
    total_size: int = 0
    extraction_time: float = 0.0
    error_message: Optional[str] = None


class ZipExtractor:
    """
    A robust ZIP file extractor with progress tracking and error handling.
    
    Features:
    - Progress callbacks for UI integration
    - Selective file extraction
    - Path traversal attack protection
    - Comprehensive error handling
    - File overwrite control
    """
    
    def __init__(self, buffer_size: int = 64 * 1024):
        """
        Initialize the ZIP extractor.
        
        Args:
            buffer_size: Size of buffer for file copy operations (bytes)
        """
        self.buffer_size = buffer_size
        self.logger = logging.getLogger(__name__)
    
    def extract_zip(self,
                   zip_path: Path,
                   target_path: Path,
                   progress_callback: Optional[Callable[[ExtractionProgress], None]] = None,
                   overwrite_existing: bool = True,
                   file_filter: Optional[Callable[[str], bool]] = None) -> ExtractionResult:
        """
        Extract a ZIP file to the target directory.
        
        Args:
            zip_path: Path to the ZIP file to extract
            target_path: Directory where files will be extracted
            progress_callback: Function to call with progress updates
            overwrite_existing: Whether to overwrite existing files
            file_filter: Optional function to filter which files to extract
            
        Returns:
            ExtractionResult: Details about the extraction operation
        """
        start_time = time.time()
        
        self.logger.info(f"Starting extraction of {zip_path} to {target_path}")
        
        try:
            # Validate inputs
            if not zip_path.exists():
                return ExtractionResult(
                    success=False,
                    error_message=f"ZIP file not found: {zip_path}"
                )
            
            if not zipfile.is_zipfile(zip_path):
                return ExtractionResult(
                    success=False,
                    error_message=f"Invalid ZIP file: {zip_path}"
                )
            
            # Create target directory
            target_path.mkdir(parents=True, exist_ok=True)
            
            # Open and analyze ZIP file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Get file information
                file_infos = zip_ref.infolist()
                
                # Filter files if filter function provided
                if file_filter:
                    file_infos = [info for info in file_infos if file_filter(info.filename)]
                
                # Calculate totals for progress tracking
                total_files = len(file_infos)
                total_bytes = sum(info.file_size for info in file_infos)
                
                self.logger.info(f"Extracting {total_files} files ({total_bytes} bytes)")
                
                # Track extraction progress
                files_extracted = 0
                bytes_extracted = 0
                
                # Extract files
                for file_info in file_infos:
                    try:
                        # Security check: prevent path traversal attacks
                        if not self._is_safe_path(file_info.filename, target_path):
                            self.logger.warning(f"Skipping unsafe path: {file_info.filename}")
                            continue
                        
                        # Calculate target file path
                        target_file_path = target_path / file_info.filename
                        
                        # Update progress callback
                        if progress_callback:
                            percentage = (bytes_extracted / total_bytes * 100) if total_bytes > 0 else 0
                            progress = ExtractionProgress(
                                current_file=file_info.filename,
                                files_extracted=files_extracted,
                                total_files=total_files,
                                bytes_extracted=bytes_extracted,
                                total_bytes=total_bytes,
                                percentage=percentage
                            )
                            progress_callback(progress)
                        
                        # Skip if file exists and overwrite is disabled
                        if target_file_path.exists() and not overwrite_existing:
                            self.logger.debug(f"Skipping existing file: {file_info.filename}")
                            files_extracted += 1
                            bytes_extracted += file_info.file_size
                            continue
                        
                        # Extract the file
                        if file_info.is_dir():
                            # Create directory
                            target_file_path.mkdir(parents=True, exist_ok=True)
                            self.logger.debug(f"Created directory: {file_info.filename}")
                        else:
                            # Extract file
                            self._extract_single_file(zip_ref, file_info, target_file_path)
                            self.logger.debug(f"Extracted file: {file_info.filename}")
                        
                        files_extracted += 1
                        bytes_extracted += file_info.file_size
                        
                    except Exception as e:
                        self.logger.error(f"Error extracting {file_info.filename}: {e}")
                        # Continue with other files rather than failing completely
                        continue
                
                # Final progress update
                if progress_callback:
                    progress = ExtractionProgress(
                        current_file="",
                        files_extracted=files_extracted,
                        total_files=total_files,
                        bytes_extracted=bytes_extracted,
                        total_bytes=total_bytes,
                        percentage=100.0
                    )
                    progress_callback(progress)
                
                extraction_time = time.time() - start_time
                
                self.logger.info(
                    f"Extraction completed: {files_extracted}/{total_files} files "
                    f"in {extraction_time:.2f}s"
                )
                
                return ExtractionResult(
                    success=True,
                    extracted_path=target_path,
                    files_extracted=files_extracted,
                    total_size=bytes_extracted,
                    extraction_time=extraction_time
                )
                
        except zipfile.BadZipFile:
            return ExtractionResult(
                success=False,
                extraction_time=time.time() - start_time,
                error_message="Corrupted ZIP file"
            )
        except OSError as e:
            return ExtractionResult(
                success=False,
                extraction_time=time.time() - start_time,
                error_message=f"File system error: {str(e)}"
            )
        except Exception as e:
            return ExtractionResult(
                success=False,
                extraction_time=time.time() - start_time,
                error_message=f"Unexpected error: {str(e)}"
            )
    
    def _extract_single_file(self, zip_ref: zipfile.ZipFile, 
                           file_info: zipfile.ZipInfo, 
                           target_path: Path) -> None:
        """
        Extract a single file from the ZIP archive.
        
        Args:
            zip_ref: Open ZIP file reference
            file_info: Information about the file to extract
            target_path: Where to extract the file
        """
        # Ensure parent directory exists
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Extract file using buffered copy for better progress tracking
        with zip_ref.open(file_info) as source:
            with open(target_path, 'wb') as target:
                shutil.copyfileobj(source, target, self.buffer_size)
        
        # Preserve file timestamps if possible
        try:
            # Convert ZIP timestamp to Unix timestamp
            timestamp = time.mktime(file_info.date_time + (0, 0, -1))
            os.utime(target_path, (timestamp, timestamp))
        except (OSError, ValueError):
            # Timestamp preservation failed, but that's not critical
            pass
    
    def _is_safe_path(self, file_path: str, target_dir: Path) -> bool:
        """
        Check if a file path is safe to extract (prevents path traversal attacks).
        
        Args:
            file_path: File path from ZIP archive
            target_dir: Target extraction directory
            
        Returns:
            bool: True if path is safe to extract
        """
        # Resolve the target path
        target_path = target_dir / file_path
        try:
            resolved_path = target_path.resolve()
            resolved_target_dir = target_dir.resolve()
            
            # Check if the resolved path is within the target directory
            return resolved_path.is_relative_to(resolved_target_dir)
        except (OSError, ValueError):
            # If we can't resolve the path, consider it unsafe
            return False
    
    def list_zip_contents(self, zip_path: Path) -> List[Dict[str, Any]]:
        """
        List the contents of a ZIP file without extracting.
        
        Args:
            zip_path: Path to the ZIP file
            
        Returns:
            List of file information dictionaries
        """
        try:
            if not zipfile.is_zipfile(zip_path):
                return []
            
            contents = []
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                for file_info in zip_ref.infolist():
                    contents.append({
                        'filename': file_info.filename,
                        'file_size': file_info.file_size,
                        'compress_size': file_info.compress_size,
                        'is_dir': file_info.is_dir(),
                        'date_time': file_info.date_time,
                        'crc': file_info.CRC
                    })
            
            return contents
            
        except Exception as e:
            self.logger.error(f"Error listing ZIP contents: {e}")
            return []
    
    def verify_zip_integrity(self, zip_path: Path) -> bool:
        """
        Verify the integrity of a ZIP file.
        
        Args:
            zip_path: Path to the ZIP file to verify
            
        Returns:
            bool: True if ZIP file is valid and not corrupted
        """
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Test the ZIP file by reading all entries
                bad_file = zip_ref.testzip()
                if bad_file is not None:
                    self.logger.error(f"Corrupted file in ZIP: {bad_file}")
                    return False
                
                self.logger.info(f"ZIP file integrity verified: {zip_path}")
                return True
                
        except zipfile.BadZipFile:
            self.logger.error(f"Invalid ZIP file: {zip_path}")
            return False
        except Exception as e:
            self.logger.error(f"Error verifying ZIP integrity: {e}")
            return False
    
    def get_zip_info(self, zip_path: Path) -> Dict[str, Any]:
        """
        Get comprehensive information about a ZIP file.
        
        Args:
            zip_path: Path to the ZIP file
            
        Returns:
            Dictionary with ZIP file information
        """
        try:
            if not zipfile.is_zipfile(zip_path):
                return {'valid': False, 'error': 'Not a valid ZIP file'}
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                file_infos = zip_ref.infolist()
                
                total_files = len(file_infos)
                total_uncompressed_size = sum(info.file_size for info in file_infos)
                total_compressed_size = sum(info.compress_size for info in file_infos)
                
                # Find root directories (for detecting nested structure)
                root_items = set()
                for info in file_infos:
                    parts = info.filename.split('/')
                    if parts[0]:  # Not empty
                        root_items.add(parts[0])
                
                return {
                    'valid': True,
                    'total_files': total_files,
                    'total_uncompressed_size': total_uncompressed_size,
                    'total_compressed_size': total_compressed_size,
                    'compression_ratio': (1 - total_compressed_size / total_uncompressed_size) if total_uncompressed_size > 0 else 0,
                    'root_items': list(root_items),
                    'has_nested_structure': len(root_items) == 1,
                    'file_size': zip_path.stat().st_size
                }
                
        except Exception as e:
            return {'valid': False, 'error': str(e)}
    
    def extract_obs_installation(self, zip_path: Path, target_path: Path,
                                progress_callback: Optional[Callable[[ExtractionProgress], None]] = None) -> ExtractionResult:
        """
        Extract OBS Studio ZIP with specific handling for OBS directory structure.
        
        OBS Studio releases typically have a nested structure where all files
        are in a subdirectory. This method can optionally flatten the structure.
        
        Args:
            zip_path: Path to the OBS Studio ZIP file
            target_path: Directory where OBS should be installed
            progress_callback: Function to call with progress updates
            
        Returns:
            ExtractionResult: Details about the extraction operation
        """
        self.logger.info("Extracting OBS Studio installation")
        
        # First, get information about the ZIP structure
        zip_info = self.get_zip_info(zip_path)
        if not zip_info['valid']:
            return ExtractionResult(
                success=False,
                error_message=zip_info['error']
            )
        
        # Check if ZIP has nested structure (common for OBS releases)
        has_nested = zip_info['has_nested_structure']
        root_items = zip_info['root_items']
        
        if has_nested and len(root_items) == 1:
            # Extract to a temporary location first
            temp_extract_path = target_path.parent / f"obs_temp_{int(time.time())}"
            
            try:
                # Extract to temporary location
                result = self.extract_zip(
                    zip_path, temp_extract_path, progress_callback
                )
                
                if not result.success:
                    return result
                
                # Move contents from nested directory to target
                nested_dir = temp_extract_path / root_items[0]
                if nested_dir.exists() and nested_dir.is_dir():
                    # Ensure target directory exists
                    target_path.mkdir(parents=True, exist_ok=True)
                    
                    # Move all contents from nested directory to target
                    for item in nested_dir.iterdir():
                        target_item = target_path / item.name
                        if target_item.exists():
                            if target_item.is_dir():
                                shutil.rmtree(target_item)
                            else:
                                target_item.unlink()
                        shutil.move(str(item), str(target_item))
                    
                    # Update result path
                    result.extracted_path = target_path
                
                # Clean up temporary directory
                shutil.rmtree(temp_extract_path, ignore_errors=True)
                
                self.logger.info("OBS Studio extraction completed with structure flattening")
                return result
                
            except Exception as e:
                # Clean up temporary directory on error
                shutil.rmtree(temp_extract_path, ignore_errors=True)
                return ExtractionResult(
                    success=False,
                    error_message=f"Error during nested extraction: {e}"
                )
        else:
            # Direct extraction - no nested structure
            return self.extract_zip(zip_path, target_path, progress_callback)