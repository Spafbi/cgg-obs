"""
Main Window UI for OBS Installer

Provides the primary user interface for the CGG OBS Studio Installer with:
- Installation path selection
- Progress tracking for downloads and extraction
- Status updates and user feedback
- Modern Qt6-based design
"""

import sys
import os
from pathlib import Path
from typing import Optional, Callable
import logging

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QProgressBar, QTextEdit,
    QFileDialog, QMessageBox, QGroupBox, QFormLayout, QCheckBox,
    QSplitter, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon, QPixmap


class StatusWidget(QFrame):
    """
    Widget for displaying status messages and progress information.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the status widget UI."""
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setLineWidth(1)
        
        layout = QVBoxLayout(self)
        
        # Status label
        self.status_label = QLabel("Ready to install OBS Studio")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setBold(True)
        self.status_label.setFont(font)
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Progress details label
        self.progress_details = QLabel("")
        self.progress_details.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_details.setVisible(False)
        layout.addWidget(self.progress_details)
    
    def set_status(self, message: str, show_progress: bool = False):
        """
        Update the status message.
        
        Args:
            message: Status message to display
            show_progress: Whether to show the progress bar
        """
        self.status_label.setText(message)
        self.progress_bar.setVisible(show_progress)
        self.progress_details.setVisible(show_progress)
    
    def update_progress(self, value: int, maximum: int = 100, details: str = ""):
        """
        Update the progress bar.
        
        Args:
            value: Current progress value
            maximum: Maximum progress value
            details: Additional progress details
        """
        self.progress_bar.setMaximum(maximum)
        self.progress_bar.setValue(value)
        self.progress_details.setText(details)


class InstallationPathWidget(QGroupBox):
    """
    Widget for selecting the OBS installation path.
    """
    
    path_changed = pyqtSignal(str)  # Emitted when path changes
    
    def __init__(self, parent=None):
        super().__init__("OBS Installation Directory", parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the installation path widget UI."""
        layout = QFormLayout(self)
        
        # Path selection layout
        path_layout = QHBoxLayout()
        
        # Path input field
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Select installation directory...")
        self.path_input.textChanged.connect(self.path_changed.emit)
        path_layout.addWidget(self.path_input)
        
        # Browse button
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.browse_for_path)
        path_layout.addWidget(self.browse_button)
        
        layout.addRow("Install to:", path_layout)
        
        # Path info label
        self.path_info = QLabel("")
        self.path_info.setWordWrap(True)
        self.path_info.setStyleSheet("color: gray; font-size: 10px;")
        layout.addRow(self.path_info)
    
    def browse_for_path(self):
        """Open a directory selection dialog."""
        current_path = self.path_input.text() or str(Path.home())
        
        selected_path = QFileDialog.getExistingDirectory(
            self,
            "Select OBS Installation Directory",
            current_path,
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
        )
        
        if selected_path:
            self.set_path(selected_path)
    
    def set_path(self, path: str):
        """
        Set the installation path.
        
        Args:
            path: Path to set
        """
        self.path_input.setText(path)
        self.update_path_info(path)
    
    def get_path(self) -> str:
        """
        Get the current installation path.
        
        Returns:
            str: Current path
        """
        return self.path_input.text()
    
    def update_path_info(self, path: str):
        """
        Update the path information display.
        
        Args:
            path: Path to analyze
        """
        if not path:
            self.path_info.setText("")
            return
        
        try:
            path_obj = Path(path)
            
            # Check if path exists
            if path_obj.exists():
                if path_obj.is_dir():
                    # Count existing files
                    try:
                        file_count = len(list(path_obj.iterdir()))
                        if file_count > 0:
                            self.path_info.setText(f"Directory exists and contains {file_count} items. Existing files may be overwritten.")
                        else:
                            self.path_info.setText("Directory exists and is empty.")
                    except PermissionError:
                        self.path_info.setText("Directory exists but cannot be accessed.")
                else:
                    self.path_info.setText("Path exists but is not a directory.")
            else:
                # Check if parent directory exists and is writable
                parent = path_obj.parent
                if parent.exists() and os.access(parent, os.W_OK):
                    self.path_info.setText("Directory will be created.")
                else:
                    self.path_info.setText("Cannot create directory (parent directory doesn't exist or is not writable).")
                    
        except Exception as e:
            self.path_info.setText(f"Error analyzing path: {e}")


class LogWidget(QGroupBox):
    """
    Widget for displaying installation logs and messages.
    """
    
    def __init__(self, parent=None):
        super().__init__("Installation Log", parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the log widget UI."""
        layout = QVBoxLayout(self)
        
        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setFont(QFont("Consolas", 9))
        layout.addWidget(self.log_text)
        
        # Log controls
        controls_layout = QHBoxLayout()
        
        # Auto-scroll checkbox
        self.auto_scroll_check = QCheckBox("Auto-scroll")
        self.auto_scroll_check.setChecked(True)
        controls_layout.addWidget(self.auto_scroll_check)
        
        controls_layout.addStretch()
        
        # Clear log button
        self.clear_button = QPushButton("Clear Log")
        self.clear_button.clicked.connect(self.clear_log)
        controls_layout.addWidget(self.clear_button)
        
        layout.addLayout(controls_layout)
    
    def append_log(self, message: str, level: str = "INFO"):
        """
        Append a message to the log.
        
        Args:
            message: Message to append
            level: Log level (INFO, WARNING, ERROR)
        """
        # Format message with timestamp
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {level}: {message}"
        
        # Add to log
        self.log_text.append(formatted_message)
        
        # Auto-scroll to bottom if enabled
        if self.auto_scroll_check.isChecked():
            cursor = self.log_text.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.log_text.setTextCursor(cursor)
    
    def clear_log(self):
        """Clear the log text."""
        self.log_text.clear()


class ControlButtonsWidget(QWidget):
    """
    Widget containing the main control buttons.
    """
    
    install_clicked = pyqtSignal()
    cancel_clicked = pyqtSignal()
    close_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the control buttons UI."""
        layout = QHBoxLayout(self)
        
        # Add stretch to push buttons to the right
        layout.addStretch()
        
        # Install button
        self.install_button = QPushButton("Install OBS Studio")
        self.install_button.clicked.connect(self.install_clicked.emit)
        self.install_button.setDefault(True)
        layout.addWidget(self.install_button)
        
        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_clicked.emit)
        self.cancel_button.setVisible(False)  # Hidden by default
        layout.addWidget(self.cancel_button)
        
        # Close button
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close_clicked.emit)
        self.close_button.setVisible(False)  # Hidden by default
        layout.addWidget(self.close_button)
    
    def set_installation_mode(self, installing: bool):
        """
        Switch between installation and normal mode.
        
        Args:
            installing: Whether installation is in progress
        """
        self.install_button.setVisible(not installing)
        self.cancel_button.setVisible(installing)
        self.close_button.setVisible(not installing)
    
    def set_completed_mode(self):
        """Switch to completed installation mode."""
        self.install_button.setVisible(False)
        self.cancel_button.setVisible(False)
        self.close_button.setVisible(True)
        self.close_button.setText("Finish")


class InstallationOptionsWidget(QFrame):
    """
    Widget for installation options (checkboxes).
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the installation options UI."""
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setLineWidth(1)
        
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Installation Options")
        title_font = QFont()
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Options checkboxes
        self.reinstall_obs_checkbox = QCheckBox("Install or update OBS Studio")
        self.reinstall_obs_checkbox.setChecked(True)
        layout.addWidget(self.reinstall_obs_checkbox)
        
        self.install_plugins_checkbox = QCheckBox("Install and update plugins")
        self.install_plugins_checkbox.setChecked(True)
        layout.addWidget(self.install_plugins_checkbox)
        
        self.create_shortcuts_checkbox = QCheckBox("Create shortcuts")
        self.create_shortcuts_checkbox.setChecked(True)
        layout.addWidget(self.create_shortcuts_checkbox)
    
    def get_options(self):
        """Get the current state of all options."""
        return {
            'reinstall_obs': self.reinstall_obs_checkbox.isChecked(),
            'install_plugins': self.install_plugins_checkbox.isChecked(),
            'create_shortcuts': self.create_shortcuts_checkbox.isChecked()
        }
    
    def set_reinstall_obs_visible(self, visible: bool):
        """Show or hide the reinstall OBS option."""
        self.reinstall_obs_checkbox.setVisible(visible)


class GitHubTokenWidget(QGroupBox):
    """
    Widget for GitHub Personal Access Token input.
    """
    
    def __init__(self, parent=None):
        super().__init__("GitHub Settings (Optional)", parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the GitHub token widget UI."""
        layout = QVBoxLayout(self)
        
        # Description
        desc_label = QLabel(
            "Enter a GitHub Personal Access Token to avoid rate limiting when downloading plugins.\n"
            "This is optional but recommended for frequent use."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: gray; font-size: 11px; margin-bottom: 5px;")
        layout.addWidget(desc_label)
        
        # Token input layout
        token_layout = QHBoxLayout()
        
        # Token label
        token_label = QLabel("Personal Access Token:")
        token_layout.addWidget(token_label)
        
        # Token input field
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)  # Hide token by default
        token_layout.addWidget(self.token_input)
        
        # Show/hide token button
        self.show_token_button = QPushButton("👁")
        self.show_token_button.setMaximumWidth(30)
        self.show_token_button.setCheckable(True)
        self.show_token_button.setToolTip("Show/hide token")
        self.show_token_button.toggled.connect(self._toggle_token_visibility)
        token_layout.addWidget(self.show_token_button)
        
        # Validate token button
        self.validate_button = QPushButton("Validate")
        self.validate_button.setMaximumWidth(80)
        self.validate_button.setToolTip("Test the GitHub token")
        self.validate_button.clicked.connect(self._validate_token)
        token_layout.addWidget(self.validate_button)
        
        layout.addLayout(token_layout)
        
        # Help link
        help_label = QLabel(
            '<a href="https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token">'
            'How to create a GitHub Personal Access Token</a>'
        )
        help_label.setOpenExternalLinks(True)
        help_label.setStyleSheet("color: #0366d6; font-size: 11px;")
        layout.addWidget(help_label)
        
        # Status label for validation results
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-size: 11px; margin-top: 5px;")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        # Save token option
        self.save_token_checkbox = QCheckBox("Remember this token (saved locally)")
        self.save_token_checkbox.setStyleSheet("font-size: 11px; color: gray;")
        layout.addWidget(self.save_token_checkbox)
    
    def _toggle_token_visibility(self, checked: bool):
        """Toggle visibility of the token text."""
        if checked:
            self.token_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_token_button.setText("🙈")
        else:
            self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_token_button.setText("👁")
    
    def _validate_token(self):
        """Validate the current GitHub token."""
        token = self.get_token()
        
        if not token:
            self._set_status("No token to validate", "gray")
            return
        
        self.validate_button.setEnabled(False)
        self.validate_button.setText("...")
        self._set_status("Validating token...", "blue")
        
        # Import and create a GitHub client to test the token
        try:
            from ..core.github_client import GitHubAPIClient
            
            # Create a temporary client with the token
            client = GitHubAPIClient(github_token=token)
            is_valid, message = client.validate_token()
            
            if is_valid:
                self._set_status(f"✓ {message}", "green")
            else:
                self._set_status(f"✗ {message}", "red")
                
        except Exception as e:
            self._set_status(f"✗ Validation error: {str(e)}", "red")
        finally:
            self.validate_button.setEnabled(True)
            self.validate_button.setText("Validate")
    
    def _set_status(self, message: str, color: str):
        """Set the status message with color."""
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 11px; margin-top: 5px;")
    
    def _toggle_token_visibility(self, checked: bool):
        """Toggle visibility of the token text."""
        if checked:
            self.token_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_token_button.setText("🙈")
        else:
            self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_token_button.setText("👁")
    
    def get_token(self) -> str:
        """Get the current token value."""
        return self.token_input.text().strip()
    
    def set_token(self, token: str):
        """Set the token value."""
        self.token_input.setText(token)
    
    def clear_token(self):
        """Clear the token field."""
        self.token_input.clear()
    
    def load_from_config(self, config_manager):
        """Load token settings from configuration."""
        if config_manager:
            # Load saved token if user chose to save it
            token = config_manager.get_github_token()
            if token:
                self.set_token(token)
                self._set_status("Token loaded from saved settings", "green")
            
            # Load save preference
            save_token = config_manager.get_save_github_token()
            self.save_token_checkbox.setChecked(save_token)
    
    def save_to_config(self, config_manager):
        """Save token settings to configuration."""
        if config_manager:
            save_token = self.save_token_checkbox.isChecked()
            config_manager.set_save_github_token(save_token)
            
            if save_token:
                token = self.get_token()
                config_manager.set_github_token(token)
                if token:
                    self._set_status("Token saved to configuration", "green")
            else:
                config_manager.clear_github_token()
                self._set_status("Token not saved (per user preference)", "gray")


class MainWindow(QMainWindow):
    """
    Main application window for the OBS installer.
    """
    
    # Define signals as class attributes
    installation_started = pyqtSignal(str, dict)  # Emitted when installation starts with path and options
    installation_cancelled = pyqtSignal()   # Emitted when installation is cancelled
    installation_complete_acknowledged = pyqtSignal(str)  # Emitted when user acknowledges installation completion dialog
    
    def __init__(self, config_manager=None):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
        self.current_install_path = ""  # Store the current installation path
        self.setup_ui()
        self.setup_connections()
        
        # Initialize with default path
        default_path = str(Path.home() / "obs")
        self.path_widget.set_path(default_path)
        
        # Load settings from config
        if self.config_manager:
            # Load GitHub token settings
            self.token_widget.load_from_config(self.config_manager)
    
    def setup_ui(self):
        """Set up the main window UI."""
        self.setWindowTitle("CGG OBS Studio Installer")
        self.setMinimumSize(600, 500)
        self.resize(700, 600)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title_label = QLabel("CGG OBS Studio Installer")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel(
            "This installer will download and install the latest version of OBS Studio for Windows."
        )
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setStyleSheet("color: gray; margin-bottom: 10px;")
        main_layout.addWidget(desc_label)
        
        # Installation path widget
        self.path_widget = InstallationPathWidget()
        main_layout.addWidget(self.path_widget)
        
        # Installation options widget
        self.options_widget = InstallationOptionsWidget()
        main_layout.addWidget(self.options_widget)
        
        # GitHub token widget
        self.token_widget = GitHubTokenWidget()
        main_layout.addWidget(self.token_widget)
        
        # Status widget
        self.status_widget = StatusWidget()
        main_layout.addWidget(self.status_widget)
        
        # Log widget
        self.log_widget = LogWidget()
        main_layout.addWidget(self.log_widget)
        
        # Control buttons
        self.control_buttons = ControlButtonsWidget()
        main_layout.addWidget(self.control_buttons)
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
    def setup_connections(self):
        """Set up signal connections."""
        # Path changes
        self.path_widget.path_changed.connect(self.on_path_changed)
        
        # Control buttons
        self.control_buttons.install_clicked.connect(self.on_install_clicked)
        self.control_buttons.cancel_clicked.connect(self.on_cancel_clicked)
        self.control_buttons.close_clicked.connect(self.close)
    
    def on_path_changed(self, path: str):
        """
        Handle installation path changes.
        
        Args:
            path: New installation path
        """
        # Validate path and update UI accordingly
        if path:
            self.control_buttons.install_button.setEnabled(True)
        else:
            self.control_buttons.install_button.setEnabled(False)
    
    def on_install_clicked(self):
        """Handle install button click."""
        install_path = self.path_widget.get_path()
        
        if not install_path:
            QMessageBox.warning(
                self, "Invalid Path", 
                "Please select a valid installation directory."
            )
            return
        
        # Get installation options
        options = self.options_widget.get_options()
        
        # Add GitHub token to options
        github_token = self.token_widget.get_token()
        if github_token:
            options['github_token'] = github_token
        
        # Save token settings if user wants to
        self.token_widget.save_to_config(self.config_manager)
        
        # Confirm installation
        actions = []
        if options['reinstall_obs']:
            actions.append("Install/update OBS Studio")
        if options['install_plugins']:
            actions.append("Download and install plugins")
        if options['create_shortcuts']:
            actions.append("Create shortcuts")
            
        if not actions:
            QMessageBox.warning(
                self, "No Actions Selected", 
                "Please select at least one installation option."
            )
            return
            
        actions_text = "\n• ".join([""] + actions)
        
        reply = QMessageBox.question(
            self, "Confirm Installation",
            f"Installation path: {install_path}\n\nActions to perform:{actions_text}\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.start_installation(install_path, options)
    
    def on_cancel_clicked(self):
        """Handle cancel button click."""
        reply = QMessageBox.question(
            self, "Cancel Installation",
            "Are you sure you want to cancel the installation?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.cancel_installation()
    
    def start_installation(self, install_path: str, options: dict = None):
        """
        Start the installation process.
        
        Args:
            install_path: Path where OBS should be installed
            options: Dictionary with installation options
        """
        if options is None:
            options = {'reinstall_obs': True, 'install_plugins': True, 'create_shortcuts': True}
            
        self.current_install_path = install_path  # Store the install path
        self.log_widget.append_log(f"Starting installation to {install_path}")
        self.status_widget.set_status("Preparing installation...", True)
        self.control_buttons.set_installation_mode(True)
        
        # Emit signal to notify controller with options
        self.installation_started.emit(install_path, options)
    
    def cancel_installation(self):
        """Cancel the installation process."""
        self.log_widget.append_log("Installation cancelled by user", "WARNING")
        self.status_widget.set_status("Installation cancelled")
        self.control_buttons.set_installation_mode(False)
        
        # Emit signal to notify controller
        self.installation_cancelled.emit()
    
    def update_status(self, message: str, show_progress: bool = False):
        """
        Update the status display.
        
        Args:
            message: Status message
            show_progress: Whether to show progress bar
        """
        self.status_widget.set_status(message, show_progress)
        self.statusBar().showMessage(message)
    
    def update_progress(self, value: int, maximum: int = 100, details: str = ""):
        """
        Update the progress display.
        
        Args:
            value: Current progress value
            maximum: Maximum progress value
            details: Additional progress details
        """
        self.status_widget.update_progress(value, maximum, details)
    
    def add_log_message(self, message: str, level: str = "INFO"):
        """
        Add a message to the log.
        
        Args:
            message: Message to add
            level: Log level
        """
        self.log_widget.append_log(message, level)
    
    def installation_completed(self, success: bool, message: str = ""):
        """
        Handle installation completion.
        
        Args:
            success: Whether installation was successful
            message: Additional message
        """
        if success:
            self.status_widget.set_status("Installation completed successfully!")
            self.add_log_message("Installation completed successfully!")
            self.control_buttons.set_completed_mode()
            
            # Show success message
            QMessageBox.information(
                self, "Installation Complete",
                f"OBS Studio has been successfully installed!\n\n{message}"
            )
            
            # After user acknowledges the completion dialog, emit signal for shortcut creation
            self.installation_complete_acknowledged.emit(self.current_install_path)
        else:
            self.status_widget.set_status("Installation failed")
            self.add_log_message(f"Installation failed: {message}", "ERROR")
            self.control_buttons.set_installation_mode(False)
            
            # Show error message
            QMessageBox.critical(
                self, "Installation Failed",
                f"Installation failed:\n\n{message}"
            )
    
    def show_info_message(self, title: str, message: str):
        """Show an information message to the user."""
        QMessageBox.information(self, title, message)
    
    def show_warning_message(self, title: str, message: str):
        """Show a warning message to the user."""
        QMessageBox.warning(self, title, message)
    
    def closeEvent(self, event):
        """Handle window close event."""
        # If installation is in progress, confirm close
        if self.control_buttons.cancel_button.isVisible():
            reply = QMessageBox.question(
                self, "Close Application",
                "Installation is in progress. Are you sure you want to close?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
        
        # Save window size and position before closing
        if self.config_manager and self.config_manager.should_remember_window_size():
            size = self.size()
            pos = self.pos()
            self.config_manager.set_window_size(size.width(), size.height())
            self.config_manager.set_window_position(pos.x(), pos.y())
        
        event.accept()


def create_application() -> QApplication:
    """
    Create and configure the Qt application.
    
    Returns:
        QApplication: Configured application instance
    """
    app = QApplication(sys.argv)
    app.setApplicationName("CGG OBS Studio Installer")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Spafbi")
    
    # Set application style
    app.setStyle("Fusion")
    
    return app


if __name__ == "__main__":
    # This allows testing the UI independently
    app = create_application()
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())