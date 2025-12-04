#!/usr/bin/env python3
"""
Cleanup script for OBS Installer

This script removes problematic packages that conflict with PyInstaller
and ensures the environment is ready for building the executable.
"""

import subprocess
import sys
import logging

def run_command(command):
    """Run a command and return success status."""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def check_and_remove_pathlib():
    """Check for and remove the obsolete pathlib package."""
    print("Checking for obsolete pathlib package...")
    
    # Check if pathlib package is installed
    success, stdout, stderr = run_command("python -m pip show pathlib")
    
    if success:
        print("⚠️  Found obsolete pathlib package!")
        print("The 'pathlib' package is a backport and conflicts with Python 3.4+'s built-in pathlib module.")
        print("Removing it...")
        
        # Remove the package
        success, stdout, stderr = run_command("python -m pip uninstall pathlib -y")
        
        if success:
            print("✅ Successfully removed obsolete pathlib package")
            return True
        else:
            print(f"❌ Failed to remove pathlib package: {stderr}")
            return False
    else:
        print("✅ No obsolete pathlib package found")
        return True

def verify_standard_pathlib():
    """Verify that the standard library pathlib is working."""
    try:
        from pathlib import Path
        test_path = Path(__file__)
        assert test_path.exists()
        print("✅ Standard library pathlib is working correctly")
        return True
    except Exception as e:
        print(f"❌ Standard library pathlib test failed: {e}")
        return False

def install_pyinstaller():
    """Install or upgrade PyInstaller."""
    print("Installing/upgrading PyInstaller...")
    
    success, stdout, stderr = run_command("python -m pip install --upgrade pyinstaller")
    
    if success:
        print("✅ PyInstaller installed/upgraded successfully")
        return True
    else:
        print(f"❌ Failed to install PyInstaller: {stderr}")
        return False

def install_requirements():
    """Install project requirements."""
    print("Installing project requirements...")
    
    success, stdout, stderr = run_command("python -m pip install -r requirements.txt")
    
    if success:
        print("✅ Project requirements installed successfully")
        return True
    else:
        print(f"❌ Failed to install requirements: {stderr}")
        print("You may need to install dependencies manually")
        return False

def main():
    """Main cleanup function."""
    print("=" * 50)
    print("OBS Installer Environment Cleanup")
    print("=" * 50)
    print()
    
    success = True
    
    # Step 1: Remove obsolete pathlib
    if not check_and_remove_pathlib():
        success = False
    
    print()
    
    # Step 2: Verify standard pathlib works
    if not verify_standard_pathlib():
        success = False
    
    print()
    
    # Step 3: Install PyInstaller
    if not install_pyinstaller():
        success = False
    
    print()
    
    # Step 4: Install requirements
    if not install_requirements():
        # This is not critical, so don't fail
        pass
    
    print()
    print("=" * 50)
    
    if success:
        print("✅ Environment cleanup completed successfully!")
        print("You can now run 'build_installer.bat' to create the executable.")
    else:
        print("❌ Some issues were encountered during cleanup.")
        print("Please resolve the errors above before building the executable.")
    
    print("=" * 50)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())