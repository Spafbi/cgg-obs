"""
Installation Worker Thread

Handles the OBS installation process in a separate thread to keep the UI responsive.
Provides progress updates and error handling for the installation workflow.
"""

import os
import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal, QObject
from PyQt6.QtWidgets import QDialog, QMessageBox

from ..core.config import ConfigManager
from ..core.github_client import GitHubAPIClient, Release
from ..utils.downloader import FileDownloader, DownloadProgress
from ..utils.extractor import ZipExtractor, ExtractionProgress


class InstallationWorker(QThread):
    """
    Worker thread for handling OBS Studio installation.
    
    Signals:
        status_updated: Emitted when installation status changes
        progress_updated: Emitted when installation progress changes
        log_message: Emitted when a log message should be displayed
        installation_finished: Emitted when installation completes (success, message)
        shortcut_creation_requested: Emitted when shortcuts should be created (install_path)
    """
    
    status_updated = pyqtSignal(str, bool)  # message, show_progress
    progress_updated = pyqtSignal(int, int, str)  # value, maximum, details
    log_message = pyqtSignal(str, str)  # message, level
    installation_finished = pyqtSignal(bool, str)  # success, message
    shortcut_creation_requested = pyqtSignal(str)  # install_path
    
    def __init__(self, install_path: str, config_manager: ConfigManager, options: dict = None):
        super().__init__()
        self.install_path = Path(install_path)
        self.config_manager = config_manager
        self.options = options or {'reinstall_obs': True, 'install_plugins': True, 'create_shortcuts': True}
        self.logger = logging.getLogger(__name__)
        
        # Components
        github_token = self.options.get('github_token') if self.options else None
        self.github_client = GitHubAPIClient(github_token=github_token)
        self.downloader = FileDownloader()
        self.extractor = ZipExtractor()
        
        # State
        self.cancelled = False
        self.current_download_path: Optional[Path] = None
    
    def run(self):
        """Main installation workflow."""
        try:
            self.log_message.emit("Starting installation process", "INFO")
            
            # Step 1: Install/Update OBS Studio if requested
            if self.options.get('reinstall_obs', True):
                self.log_message.emit("Installing/updating OBS Studio", "INFO")
                
                # Check for latest release
                self.status_updated.emit("Checking for latest OBS Studio release...", True)
                latest_release = self._get_latest_release()
                if not latest_release:
                    self.installation_finished.emit(False, "Failed to get latest OBS Studio release information")
                    return
                
                # Check if we need to download
                need_download = self._check_if_download_needed(latest_release)
                download_path = None
                
                if need_download:
                    # Download OBS Studio
                    download_path = self._download_obs_release(latest_release)
                    if not download_path:
                        self.installation_finished.emit(False, "Failed to download OBS Studio")
                        return
                else:
                    # Use existing download - get the correct filename from the release
                    asset = self.github_client.get_windows_x64_asset(latest_release)
                    if asset:
                        cache_dir = Path(self.config_manager.get_download_cache_dir())
                        download_path = cache_dir / asset.name
                        self.log_message.emit(f"Using existing download: {download_path.name}", "INFO")
                    else:
                        self.installation_finished.emit(False, "Failed to get release asset information")
                        return
                
                if self.cancelled:
                    return
                
                # Extract OBS Studio
                if download_path:
                    success = self._extract_obs_studio(download_path)
                    if not success:
                        self.installation_finished.emit(False, "Failed to extract OBS Studio")
                        return
                
                if self.cancelled:
                    return
                
                # Update configuration
                self._update_configuration(latest_release)
            else:
                self.log_message.emit("Skipping OBS Studio installation", "INFO")
            
            # Step 2: Install plugins if requested
            if self.options.get('install_plugins', True):
                self.log_message.emit("Installing plugins", "INFO")
                self._download_plugins()
            else:
                self.log_message.emit("Skipping plugin installation", "INFO")
            
            if self.cancelled:
                return
            
            # Step 3: Request shortcut creation if requested
            if self.options.get('create_shortcuts', True):
                self.log_message.emit("Requesting shortcut creation", "INFO")
                self.shortcut_creation_requested.emit(str(self.install_path))
                # Don't emit installation_finished yet - wait for shortcuts to complete
            else:
                self.log_message.emit("Skipping shortcut creation", "INFO")
                # No shortcuts needed, so we can complete now
                self._emit_final_completion()
            
        except Exception as e:
            self.logger.error(f"Installation failed with exception: {e}")
            self.installation_finished.emit(False, f"Installation failed: {str(e)}")
    
    def _emit_final_completion(self):
        """Emit the final installation completion message."""
        self.log_message.emit("Installation process completed successfully!", "INFO")
        completed_actions = []
        if self.options.get('reinstall_obs', True):
            completed_actions.append("OBS Studio installed")
        if self.options.get('install_plugins', True):
            completed_actions.append("Plugins downloaded and extracted")
        if self.options.get('create_shortcuts', True):
            completed_actions.append("Shortcuts created")
            
        message = f"Installation completed successfully:\n• " + "\n• ".join(completed_actions)
        self.installation_finished.emit(True, message)
    
    def cancel(self):
        """Cancel the installation process."""
        self.cancelled = True
        self.log_message.emit("Cancelling installation...", "WARNING")
        
        # Clean up partial download if exists
        if self.current_download_path and self.current_download_path.exists():
            try:
                self.downloader.cleanup_partial_download(self.current_download_path)
            except Exception as e:
                self.logger.error(f"Failed to cleanup partial download: {e}")
    
    def _download_plugins(self):
        """Download OBS plugins."""
        try:
            self.status_updated.emit("Downloading OBS plugins...", True)
            self.log_message.emit("Starting plugin downloads", "INFO")
            
            # Find plugins.json file using resource utilities
            from ..utils.resources import get_plugins_json_path
            plugins_json_path = get_plugins_json_path()
            
            if not plugins_json_path.exists():
                self.log_message.emit(f"Plugins configuration not found at {plugins_json_path}", "WARNING")
                return
            
            from ..utils.plugin_manager import OBSPluginManager
            
            # Create plugin manager with OBS installation directory and GitHub token
            github_token = self.options.get('github_token') if self.options else None
            plugin_manager = OBSPluginManager(self.config_manager, self.install_path, github_token)
            
            # Progress callback for UI updates
            def progress_callback(current: int, total: int, message: str):
                percentage = int((current / total) * 100) if total > 0 else 0
                self.progress_updated.emit(percentage, 100, message)
                self.status_updated.emit(f"Downloading and extracting plugins... ({current}/{total})", True)
            
            # Download all plugins
            successful, total, errors = plugin_manager.download_all_plugins(
                plugins_json_path, 
                progress_callback
            )
            
            # Log results
            if successful == total:
                self.log_message.emit(f"All {total} plugins downloaded and extracted successfully", "INFO")
            elif successful > 0:
                self.log_message.emit(f"Downloaded {successful}/{total} plugins (some failed)", "WARNING")
                for error in errors[:3]:  # Log first 3 errors
                    self.log_message.emit(f"Plugin error: {error}", "ERROR")
            else:
                self.log_message.emit("All plugin downloads failed", "ERROR")
                for error in errors[:3]:  # Log first 3 errors
                    self.log_message.emit(f"Plugin error: {error}", "ERROR")
                    
        except Exception as e:
            self.log_message.emit(f"Error during plugin download: {e}", "ERROR")
            self.logger.error(f"Error during plugin download: {e}")
    
    def _get_latest_release(self) -> Optional[Release]:
        """Get the latest OBS Studio release."""
        try:
            latest_release = self.github_client.get_latest_release(include_prerelease=False)
            if latest_release:
                self.log_message.emit(f"Found latest release: {latest_release.tag_name}", "INFO")
                return latest_release
            else:
                self.log_message.emit("Failed to get latest release information", "ERROR")
                return None
        except Exception as e:
            self.log_message.emit(f"Error getting latest release: {e}", "ERROR")
            return None
    
    def _check_if_download_needed(self, release: Release) -> bool:
        """Check if we need to download the release."""
        # Get the expected filename for this release
        asset = self.github_client.get_windows_x64_asset(release)
        if not asset:
            self.log_message.emit("No Windows x64 asset found in release", "WARNING")
            return True  # Need to download
        
        # Check if we already have this exact file
        cache_dir = Path(self.config_manager.get_download_cache_dir())
        expected_file = cache_dir / asset.name
        
        if expected_file.exists():
            self.log_message.emit(f"Version {release.tag_name} already downloaded: {asset.name}", "INFO")
            # Update last version in case it wasn't recorded
            self.config_manager.set_last_obs_version(release.tag_name)
            return False
        
        self.log_message.emit(f"Need to download version {release.tag_name}: {asset.name}", "INFO")
        return True
    
    def _download_obs_release(self, release: Release) -> Optional[Path]:
        """Download the OBS Studio release."""
        try:
            # Find Windows x64 asset
            asset = self.github_client.get_windows_x64_asset(release)
            if not asset:
                self.log_message.emit("No Windows x64 asset found in release", "ERROR")
                return None
            
            self.log_message.emit(f"Downloading {asset.name} ({asset.size} bytes)", "INFO")
            
            # Prepare download
            cache_dir = Path(self.config_manager.get_download_cache_dir())
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            download_path = cache_dir / asset.name
            self.current_download_path = download_path
            
            # Set up progress callback
            def progress_callback(progress: DownloadProgress):
                if self.cancelled:
                    return
                
                percentage = int(progress.percentage)
                details = f"Downloaded {progress.downloaded_bytes:,} / {progress.total_bytes:,} bytes"
                if progress.speed_bps > 0:
                    speed_mb = progress.speed_bps / (1024 * 1024)
                    details += f" ({speed_mb:.1f} MB/s)"
                
                self.progress_updated.emit(percentage, 100, details)
            
            self.status_updated.emit("Downloading OBS Studio...", True)
            
            # Download the file
            result = self.downloader.download_file(
                asset.download_url,
                cache_dir,
                asset.name,
                progress_callback
            )
            
            if result.success:
                self.log_message.emit(f"Download completed: {result.file_path}", "INFO")
                return result.file_path
            else:
                self.log_message.emit(f"Download failed: {result.error_message}", "ERROR")
                return None
                
        except Exception as e:
            self.log_message.emit(f"Error during download: {e}", "ERROR")
            return None
    
    def _extract_obs_studio(self, zip_path: Path) -> bool:
        """Extract OBS Studio from ZIP file."""
        try:
            self.log_message.emit(f"Extracting {zip_path.name} to {self.install_path}", "INFO")
            
            # Set up progress callback
            def progress_callback(progress: ExtractionProgress):
                if self.cancelled:
                    return
                
                percentage = int(progress.percentage)
                details = f"Extracted {progress.files_extracted} / {progress.total_files} files"
                if progress.current_file:
                    details += f"\nCurrent: {progress.current_file}"
                
                self.progress_updated.emit(percentage, 100, details)
            
            self.status_updated.emit("Extracting OBS Studio...", True)
            
            # Extract the files
            result = self.extractor.extract_obs_installation(
                zip_path,
                self.install_path,
                progress_callback
            )
            
            if result.success:
                self.log_message.emit(
                    f"Extraction completed: {result.files_extracted} files extracted", "INFO"
                )
                return True
            else:
                self.log_message.emit(f"Extraction failed: {result.error_message}", "ERROR")
                return False
                
        except Exception as e:
            self.log_message.emit(f"Error during extraction: {e}", "ERROR")
            return False
    
    def _update_configuration(self, release: Release):
        """Update configuration with new installation information."""
        try:
            # Update last known version
            self.config_manager.set_last_obs_version(release.tag_name)
            
            # Update installation path
            self.config_manager.set_install_path(str(self.install_path))
            
            self.log_message.emit("Configuration updated", "INFO")
            
        except Exception as e:
            self.log_message.emit(f"Warning: Failed to update configuration: {e}", "WARNING")


class InstallationController(QObject):
    """
    Controller that integrates the installation worker with the UI.
    """
    
    def __init__(self, main_window, config_manager: ConfigManager):
        super().__init__()
        self.main_window = main_window
        self.config_manager = config_manager
        self.worker: Optional[InstallationWorker] = None
        self.logger = logging.getLogger(__name__)
        
        # Connect UI signals
        self._setup_ui_connections()
        
        # Load saved configuration
        self._load_saved_configuration()
    
    def _setup_ui_connections(self):
        """Set up connections between UI and controller."""
        # Connect existing signals from the main window
        self.main_window.installation_started.connect(self._on_installation_started)
        self.main_window.installation_cancelled.connect(self.cancel_installation)
    
    def _on_installation_started(self, install_path: str, options: dict):
        """Handle installation started with options."""
        self.start_installation(install_path, options)
    
    def _load_saved_configuration(self):
        """Load saved configuration into the UI."""
        try:
            # Load saved installation path
            saved_path = self.config_manager.get_install_path()
            if saved_path:
                self.main_window.path_widget.set_path(saved_path)
            
            # Load window size and position if enabled
            if self.config_manager.should_remember_window_size():
                width, height = self.config_manager.get_window_size()
                self.main_window.resize(width, height)
                
                x, y = self.config_manager.get_window_position()
                if x >= 0 and y >= 0:
                    self.main_window.move(x, y)
                
        except Exception as e:
            self.main_window.add_log_message(f"Warning: Failed to load saved configuration: {e}", "WARNING")
    
    def start_installation(self, install_path: str, options: dict = None):
        """
        Start the installation process.
        
        Args:
            install_path: Path where OBS should be installed
            options: Dictionary with installation options (reinstall_obs, install_plugins, create_shortcuts)
        """
        if self.worker and self.worker.isRunning():
            self.main_window.add_log_message("Installation already in progress", "WARNING")
            return
        
        # Default options if none provided
        if options is None:
            options = {'reinstall_obs': True, 'install_plugins': True, 'create_shortcuts': True}
        
        try:
            # Create and configure worker
            self.worker = InstallationWorker(install_path, self.config_manager, options)
            
            # Connect worker signals
            self.worker.status_updated.connect(self.main_window.update_status)
            self.worker.progress_updated.connect(self.main_window.update_progress)
            self.worker.log_message.connect(self.main_window.add_log_message)
            self.worker.installation_finished.connect(self._on_installation_finished)
            self.worker.shortcut_creation_requested.connect(self._on_shortcut_creation_requested)
            
            # Start the worker
            self.worker.start()
            
        except Exception as e:
            self.main_window.installation_completed(False, f"Failed to start installation: {e}")
    
    def cancel_installation(self):
        """Cancel the current installation."""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(5000)  # Wait up to 5 seconds for clean shutdown
            if self.worker.isRunning():
                self.worker.terminate()
                self.main_window.add_log_message("Installation forcibly terminated", "WARNING")
            else:
                self.main_window.add_log_message("Installation cancelled", "INFO")
            
            self.main_window.update_status("Installation cancelled")
            self.main_window.control_buttons.set_installation_mode(False)
    
    def _on_installation_finished(self, success: bool, message: str):
        """Handle installation completion."""
        # Save window size and position if enabled
        if self.config_manager.should_remember_window_size():
            size = self.main_window.size()
            pos = self.main_window.pos()
            self.config_manager.set_window_size(size.width(), size.height())
            self.config_manager.set_window_position(pos.x(), pos.y())
        
        # Update UI
        self.main_window.installation_completed(success, message)
        
        # Clean up worker
        if self.worker:
            self.worker.deleteLater()
            self.worker = None

    def _on_shortcut_creation_requested(self, install_path: str):
        """Handle shortcut creation request."""
        try:
            from ..ui.icon_selection import IconSelectionDialog
            from ..utils.shortcuts import WindowsShortcutCreator
            
            # Convert string path to Path object
            install_path_obj = Path(install_path)
            
            # Update status to show shortcut creation is starting
            self.main_window.update_status("Setting up shortcuts...")
            
            # Show icon selection dialog (it handles shortcut options internally)
            dialog = IconSelectionDialog(install_path_obj, self.main_window, self.config_manager)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # The dialog's create_shortcuts method handles everything
                self.logger.info("Shortcut creation completed via dialog")
                self.main_window.update_status("Shortcuts created successfully!")
                # Now show the final completion
                self._show_final_completion(True)
            else:
                self.logger.info("Shortcut creation cancelled by user")
                self.main_window.update_status("Shortcut creation cancelled")
                # Still show completion but note shortcuts were skipped
                self._show_final_completion(False)
            
        except Exception as e:
            self.logger.error(f"Error during shortcut creation: {e}")
            self.main_window.show_warning_message(
                "Shortcut Creation Error",
                f"An error occurred while creating shortcuts: {str(e)}"
            )
            # Show completion with error
            self._show_final_completion(False)
    
    def _show_final_completion(self, shortcuts_created: bool):
        """Show the final installation completion message."""
        if not self.worker or not hasattr(self.worker, 'options'):
            return
            
        completed_actions = []
        if self.worker.options.get('reinstall_obs', True):
            completed_actions.append("OBS Studio installed")
        if self.worker.options.get('install_plugins', True):
            completed_actions.append("Plugins downloaded and extracted")
        if self.worker.options.get('create_shortcuts', True):
            if shortcuts_created:
                completed_actions.append("Shortcuts created")
            else:
                completed_actions.append("Shortcuts skipped")
                
        message = f"Installation completed successfully:\n• " + "\n• ".join(completed_actions)
        self.main_window.installation_completed(True, message)