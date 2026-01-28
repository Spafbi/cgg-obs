"""
Winget Package Manager

Handles installing external dependencies via Windows Package Manager (winget).
Reads configuration from winget.json.
"""

import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from .resources import get_winget_json_path


class WingetManager:
    """
    Manages installation of packages via winget.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.winget_json_path = get_winget_json_path()
        
    def is_available(self) -> bool:
        """Check if winget is available on the system."""
        return shutil.which("winget") is not None
        
    def load_config(self) -> Dict[str, List[str]]:
        """
        Load package configuration from winget.json.
        
        Returns:
            Dict mapping group names to lists of package IDs
        """
        if not self.winget_json_path.exists():
            self.logger.info("winget.json not found, skipping winget operations")
            return {}
            
        try:
            with open(self.winget_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.logger.info(f"Loaded winget configuration with {len(data)} groups")
                return data
        except Exception as e:
            self.logger.error(f"Failed to load winget.json: {e}")
            return {}
            
    def get_all_packages(self) -> List[str]:
        """Get a flat list of all packages to install."""
        config = self.load_config()
        packages = []
        for group_packages in config.values():
            if isinstance(group_packages, list):
                packages.extend(group_packages)
        return list(set(packages))  # Remove duplicates
        
    def install_packages(self, progress_callback: Optional[callable] = None) -> Tuple[bool, List[str]]:
        """
        Install all configured packages using winget.
        
        Args:
            progress_callback: Optional callback for progress updates
            
        Returns:
            Tuple of (success, error_messages)
        """
        if not self.is_available():
            return False, ["winget is not available on this system"]
            
        packages = self.get_all_packages()
        if not packages:
            return True, []  # Nothing to install
            
        self.logger.info(f"Installing {len(packages)} packages via winget: {', '.join(packages)}")
        
        if progress_callback:
            progress_callback(0, 1, "Starting winget installation...")
            
        # Construct command
        # We use --accept-source-agreements and --accept-package-agreements to avoid prompts
        cmd = ["winget", "install"] + packages + [
            "--accept-source-agreements", 
            "--accept-package-agreements"
        ]
        
        try:
            # Run winget
            # Using shell=True on Windows can help resolve the winget alias in some environments,
            # but standard execution is preferred if shutil.which found it.
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            
            if process.returncode == 0:
                self.logger.info("Winget installation completed successfully")
                return True, []
            else:
                error_msg = f"Winget exited with code {process.returncode}"
                if process.stderr:
                    error_msg += f": {process.stderr}"
                elif process.stdout:
                    error_msg += f"\nOutput: {process.stdout}"
                    
                self.logger.error(error_msg)
                return False, [error_msg]
                
        except Exception as e:
            self.logger.error(f"Failed to execute winget: {e}")
            return False, [str(e)]
