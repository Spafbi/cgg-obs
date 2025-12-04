"""
Icon Selection Dialog for OBS Installer

Provides a Qt6 dialog for users to select which icon to use for OBS shortcuts.
Displays available icons with previews and allows selection.
"""

import logging
from pathlib import Path
from typing import Optional, List

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QButtonGroup, QRadioButton, QMessageBox,
    QGroupBox, QCheckBox, QFrame, QSizePolicy, QLineEdit
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QPixmap, QFont, QIcon

from ..utils.shortcuts import WindowsShortcutCreator
from ..utils.resources import get_icons_directory, list_available_icons


class IconPreviewWidget(QFrame):
    """
    Widget that displays an icon preview with selection capability.
    """
    
    icon_selected = pyqtSignal(str)  # Emitted when icon is selected
    
    def __init__(self, icon_path: Path, display_name: str, parent=None):
        super().__init__(parent)
        self.icon_path = icon_path
        self.display_name = display_name
        self.is_selected = False
        
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the icon preview widget UI."""
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setLineWidth(1)
        self.setFixedSize(150, 180)  # Larger size to accommodate 128x128 icons
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(5)
        
        # Icon display
        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setFixedSize(132, 132)  # Sized for 128x128 icon + minimal border
        self.icon_label.setStyleSheet("""
            border: 1px solid gray; 
            background-color: white;
            padding: 1px;
        """)
        self.icon_label.setScaledContents(False)  # Prevent automatic scaling that can blur
        
        # Load and display icon
        self.load_icon()
        
        layout.addWidget(self.icon_label)
        
        # Radio button for selection
        self.radio_button = QRadioButton()
        self.radio_button.toggled.connect(self.on_selection_changed)
        layout.addWidget(self.radio_button, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Icon name label
        name_label = QLabel(self.display_name)
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setMaximumWidth(140)  # Increased for larger icon container
        
        font = QFont()
        font.setPointSize(8)
        name_label.setFont(font)
        
        layout.addWidget(name_label)
        
        # Make the whole widget clickable
        self.setStyleSheet("""
            IconPreviewWidget {
                border: 2px solid transparent;
                border-radius: 5px;
                background-color: palette(base);
            }
            IconPreviewWidget:hover {
                border: 2px solid palette(highlight);
                background-color: palette(alternate-base);
            }
        """)
    
    def load_icon(self):
        """Load and display the icon."""
        try:
            # For ICO files, try to load specific sizes
            if self.icon_path.suffix.lower() == '.ico':
                pixmap = self.load_ico_at_size(self.icon_path, 128)  # Get 128x128 for best quality
            else:
                # For other formats, load normally and scale to 128x128 if needed
                original_pixmap = QPixmap(str(self.icon_path))
                if not original_pixmap.isNull():
                    # Always scale to exactly 128x128 for consistency
                    pixmap = original_pixmap.scaled(
                        128, 128,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                else:
                    pixmap = original_pixmap
            
            if not pixmap.isNull():
                # Display the 128x128 icon directly without downscaling
                self.icon_label.setPixmap(pixmap)
            else:
                self.icon_label.setText("No Preview")
        except Exception as e:
            logging.getLogger(__name__).warning(f"Could not load icon {self.icon_path}: {e}")
            self.icon_label.setText("Error")
    
    def load_ico_at_size(self, ico_path: Path, preferred_size: int) -> QPixmap:
        """
        Load an ICO file at a specific size.
        
        Args:
            ico_path: Path to the ICO file
            preferred_size: Preferred icon size (e.g., 128)
            
        Returns:
            QPixmap with the icon at the requested size
        """
        from PyQt6.QtGui import QIcon
        
        # Load as QIcon which can handle multiple sizes in ICO files
        icon = QIcon(str(ico_path))
        
        if not icon.isNull():
            # Get available sizes
            available_sizes = icon.availableSizes()
            
            if available_sizes:
                # Try to find exact size match first
                exact_match = None
                for size in available_sizes:
                    if size.width() == preferred_size and size.height() == preferred_size:
                        exact_match = size
                        break
                
                if exact_match:
                    # Perfect! Use the exact 128x128 size
                    pixmap = icon.pixmap(exact_match)
                    logging.getLogger(__name__).info(
                        f"Found exact {preferred_size}x{preferred_size} size in ICO"
                    )
                else:
                    # No exact match - use the largest available size and scale to 128x128
                    largest_size = max(available_sizes, key=lambda s: s.width() * s.height())
                    large_pixmap = icon.pixmap(largest_size)
                    
                    # Scale the largest size to exactly 128x128
                    pixmap = large_pixmap.scaled(
                        preferred_size,
                        preferred_size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    
                    logging.getLogger(__name__).info(
                        f"Scaled {largest_size.width()}x{largest_size.height()} icon to {preferred_size}x{preferred_size}"
                    )
                
                logging.getLogger(__name__).info(
                    f"Available ICO sizes: {[(s.width(), s.height()) for s in available_sizes]}"
                )
                
                return pixmap
        
        # Fallback to regular loading if QIcon approach fails
        return QPixmap(str(ico_path))
    
    def mousePressEvent(self, event):
        """Handle mouse clicks to select the icon."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.radio_button.setChecked(True)
        super().mousePressEvent(event)
    
    def on_selection_changed(self, checked: bool):
        """Handle selection state changes."""
        self.is_selected = checked
        if checked:
            self.icon_selected.emit(str(self.icon_path))
            self.setStyleSheet("""
                IconPreviewWidget {
                    border: 2px solid palette(highlight);
                    background-color: palette(alternate-base);
                }
            """)
        else:
            self.setStyleSheet("""
                IconPreviewWidget {
                    border: 2px solid transparent;
                    background-color: palette(base);
                }
                IconPreviewWidget:hover {
                    border: 2px solid palette(highlight);
                    background-color: palette(alternate-base);
                }
            """)
    
    def set_selected(self, selected: bool):
        """Programmatically set selection state."""
        self.radio_button.setChecked(selected)


class IconSelectionDialog(QDialog):
    """
    Dialog for selecting an icon for OBS shortcuts.
    """
    
    def __init__(self, installation_path: Path, parent=None, config_manager=None):
        super().__init__(parent)
        self.installation_path = installation_path
        self.config_manager = config_manager
        self.selected_icon_path: Optional[Path] = None
        self.create_desktop_shortcut = True
        self.create_start_menu_shortcut = True
        
        # Find the installer's icons directory using resource utilities
        self.installer_icons_dir = get_icons_directory()
        
        self.shortcut_creator = WindowsShortcutCreator()
        self.icon_widgets: List[IconPreviewWidget] = []
        self.button_group = QButtonGroup()
        
        self.setup_ui()
        self.load_icons()
    
    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Select Shortcut Icon")
        self.setModal(True)
        self.resize(600, 500)
        
        layout = QVBoxLayout(self)
        
        # Title and description
        title_label = QLabel("Select Icon for OBS Studio Shortcuts")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        desc_label = QLabel(
            "Choose an icon that will be used for the OBS Studio shortcuts. "
            "The selected icon will appear on your desktop and in the Start menu."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: gray; margin: 10px;")
        layout.addWidget(desc_label)
        
        # Shortcut name input
        name_group = QGroupBox("Shortcut Name")
        name_layout = QVBoxLayout(name_group)
        
        name_desc = QLabel("Enter the name for the shortcuts:")
        name_desc.setStyleSheet("color: gray;")
        name_layout.addWidget(name_desc)
        
        self.shortcut_name_edit = QLineEdit()
        # Load saved shortcut name or use default
        if self.config_manager:
            saved_name = self.config_manager.get_shortcut_name()
            self.shortcut_name_edit.setText(saved_name)
        else:
            self.shortcut_name_edit.setText("Chaotic Good Gaming OBS")  # Fallback default
        self.shortcut_name_edit.setPlaceholderText("Enter shortcut name...")
        
        # Save shortcut name when user finishes editing (loses focus or presses Enter)
        if self.config_manager:
            self.shortcut_name_edit.editingFinished.connect(self._save_shortcut_name)
        
        name_layout.addWidget(self.shortcut_name_edit)
        
        layout.addWidget(name_group)
        
        # Shortcut options
        options_group = QGroupBox("Shortcut Options")
        options_layout = QVBoxLayout(options_group)
        
        self.desktop_checkbox = QCheckBox("Create Desktop Shortcut")
        self.desktop_checkbox.setChecked(True)
        self.desktop_checkbox.toggled.connect(self.on_desktop_option_changed)
        options_layout.addWidget(self.desktop_checkbox)
        
        self.start_menu_checkbox = QCheckBox("Create Start Menu Shortcut")
        self.start_menu_checkbox.setChecked(True)
        self.start_menu_checkbox.toggled.connect(self.on_start_menu_option_changed)
        options_layout.addWidget(self.start_menu_checkbox)
        
        layout.addWidget(options_group)
        
        # Icon selection area
        icon_group = QGroupBox("Available Icons")
        icon_group_layout = QVBoxLayout(icon_group)
        
        # Scroll area for icons
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(250)
        
        self.icon_container = QWidget()
        self.icon_layout = QGridLayout(self.icon_container)
        self.icon_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        scroll_area.setWidget(self.icon_container)
        icon_group_layout.addWidget(scroll_area)
        
        layout.addWidget(icon_group)
        
        # Status label
        self.status_label = QLabel("Loading icons...")
        self.status_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.status_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.skip_button = QPushButton("Skip Shortcuts")
        self.skip_button.clicked.connect(self.skip_shortcuts)
        button_layout.addWidget(self.skip_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.create_button = QPushButton("Create Shortcuts")
        self.create_button.clicked.connect(self.create_shortcuts)
        self.create_button.setDefault(True)
        self.create_button.setEnabled(False)  # Enabled when icon is selected
        button_layout.addWidget(self.create_button)
        
        layout.addLayout(button_layout)
    
    def find_installer_icons(self) -> List[Path]:
        """
        Find available icon files using the resource utilities.
        
        Returns:
            List of paths to icon files
        """
        return list_available_icons()
    
    def load_icons(self):
        """Load and display available icons."""
        try:
            # Find available icons in the installer's icons directory
            icon_paths = self.find_installer_icons()
            
            if not icon_paths:
                self.status_label.setText("No icons found in installer icons directory.")
                return
            
            # Clear existing widgets
            for widget in self.icon_widgets:
                widget.setParent(None)
            self.icon_widgets.clear()
            
            # Add icon widgets
            row = 0
            col = 0
            max_cols = 4
            
            for icon_path in icon_paths:
                # Create simple display name from filename
                display_name = icon_path.stem  # Filename without extension
                
                icon_widget = IconPreviewWidget(icon_path, display_name)
                icon_widget.icon_selected.connect(self.on_icon_selected)
                
                self.icon_widgets.append(icon_widget)
                self.button_group.addButton(icon_widget.radio_button)
                
                self.icon_layout.addWidget(icon_widget, row, col)
                
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1
            
            # Auto-select saved icon or first icon
            selected_widget = None
            if self.config_manager:
                saved_icon_path = self.config_manager.get_selected_icon_path()
                if saved_icon_path:
                    # Try to find the saved icon in the current list
                    for widget in self.icon_widgets:
                        if str(widget.icon_path) == saved_icon_path:
                            # Verify the file still exists
                            if widget.icon_path.exists():
                                selected_widget = widget
                                break
                    
                    # If saved icon path doesn't exist anymore, clear it from config
                    if not selected_widget and saved_icon_path:
                        from pathlib import Path
                        if not Path(saved_icon_path).exists():
                            self.config_manager.clear_selected_icon_path()
            
            # Fall back to first icon if saved icon not found or no saved icon
            if not selected_widget and self.icon_widgets:
                selected_widget = self.icon_widgets[0]
            
            if selected_widget:
                selected_widget.set_selected(True)
            
            self.status_label.setText(f"Found {len(icon_paths)} icons. Select one to use for shortcuts.")
            
        except Exception as e:
            self.status_label.setText(f"Error loading icons: {e}")
            logging.getLogger(__name__).error(f"Error loading icons: {e}")
    
    def on_icon_selected(self, icon_path: str):
        """Handle icon selection."""
        self.selected_icon_path = Path(icon_path)
        self.create_button.setEnabled(True)
        
        # Save the selected icon path to config for future use
        if self.config_manager:
            self.config_manager.set_selected_icon_path(icon_path)
        
        # Update status
        icon_name = self.selected_icon_path.name
        self.status_label.setText(f"Selected icon: {icon_name}")
    
    def on_desktop_option_changed(self, checked: bool):
        """Handle desktop shortcut option change."""
        self.create_desktop_shortcut = checked
        self.update_create_button_state()
    
    def on_start_menu_option_changed(self, checked: bool):
        """Handle start menu shortcut option change."""
        self.create_start_menu_shortcut = checked
        self.update_create_button_state()
    
    def update_create_button_state(self):
        """Update the create button enabled state."""
        has_icon = self.selected_icon_path is not None
        has_options = self.create_desktop_shortcut or self.create_start_menu_shortcut
        self.create_button.setEnabled(has_icon and has_options)
    
    def _save_shortcut_name(self):
        """Save the current shortcut name to config when user finishes editing."""
        if self.config_manager:
            shortcut_name = self.shortcut_name_edit.text().strip()
            if shortcut_name:  # Only save if not empty
                self.config_manager.set_shortcut_name(shortcut_name)
    
    def create_shortcuts(self):
        """Create the shortcuts with selected options."""
        if not self.selected_icon_path:
            QMessageBox.warning(self, "No Icon Selected", "Please select an icon first.")
            return
        
        if not (self.create_desktop_shortcut or self.create_start_menu_shortcut):
            QMessageBox.warning(self, "No Options Selected", "Please select at least one shortcut option.")
            return
        
        # Get the shortcut name from the input field
        shortcut_name = self.shortcut_name_edit.text().strip()
        if not shortcut_name:
            QMessageBox.warning(self, "No Name Entered", "Please enter a name for the shortcuts.")
            return
        
        # Save the shortcut name to config for future use
        if self.config_manager:
            self.config_manager.set_shortcut_name(shortcut_name)
        
        try:
            success, errors = self.shortcut_creator.create_obs_shortcuts(
                installation_path=self.installation_path,
                icon_path=self.selected_icon_path,
                create_desktop=self.create_desktop_shortcut,
                create_start_menu=self.create_start_menu_shortcut,
                shortcut_name=shortcut_name
            )
            
            if success:
                # Shortcuts created successfully - just close the dialog
                self.accept()
            else:
                error_msg = "Failed to create shortcuts:\n• " + "\n• ".join(errors)
                QMessageBox.critical(self, "Shortcut Creation Failed", error_msg)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while creating shortcuts:\n{e}")
    
    def skip_shortcuts(self):
        """Skip shortcut creation."""
        reply = QMessageBox.question(
            self, "Skip Shortcuts",
            "Are you sure you want to skip creating shortcuts?\n"
            "You can create them manually later if needed.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.reject()
    
    def get_selection_info(self) -> tuple[Optional[Path], bool, bool]:
        """
        Get the current selection information.
        
        Returns:
            Tuple of (selected_icon_path, create_desktop, create_start_menu)
        """
        return (
            self.selected_icon_path,
            self.create_desktop_shortcut,
            self.create_start_menu_shortcut
        )
    
    def get_selected_icon(self) -> Optional[Path]:
        """
        Get the selected icon path.
        
        Returns:
            Path to the selected icon file, or None if no icon selected
        """
        return self.selected_icon_path


def show_icon_selection_dialog(installation_path: Path, parent=None, config_manager=None) -> bool:
    """
    Show the icon selection dialog and create shortcuts.
    
    Args:
        installation_path: Path to OBS installation
        parent: Parent widget
        config_manager: Optional config manager for persistence
        
    Returns:
        bool: True if shortcuts were created, False if skipped/cancelled
    """
    try:
        dialog = IconSelectionDialog(installation_path, parent, config_manager)
        result = dialog.exec()
        return result == QDialog.DialogCode.Accepted
    except Exception as e:
        logging.getLogger(__name__).error(f"Error showing icon selection dialog: {e}")
        return False