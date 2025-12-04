#!/usr/bin/env python3
"""
Debug script to verify PyInstaller data file bundling

This script helps diagnose issues with PyInstaller not including data files
by checking the spec file configuration and verifying file paths.
"""

import sys
from pathlib import Path

def main():
    print("=" * 60)
    print("PyInstaller Data Files Debug")
    print("=" * 60)
    
    # Get project root
    project_root = Path(__file__).parent
    print(f"Project root: {project_root}")
    print()
    
    # Check for spec file
    spec_file = project_root / "obs_installer.spec"
    print(f"Spec file: {spec_file}")
    print(f"Spec file exists: {spec_file.exists()}")
    print()
    
    # Check for data files
    icons_dir = project_root / "icons"
    plugins_json = project_root / "plugins.json"
    
    print("Data files check:")
    print(f"  Icons directory: {icons_dir}")
    print(f"  Icons exists: {icons_dir.exists()}")
    
    if icons_dir.exists():
        icon_files = list(icons_dir.glob('*'))
        print(f"  Icon files ({len(icon_files)}):")
        for icon in icon_files:
            if icon.is_file():
                print(f"    - {icon.name} ({icon.stat().st_size} bytes)")
    
    print(f"  Plugins JSON: {plugins_json}")
    print(f"  Plugins JSON exists: {plugins_json.exists()}")
    
    if plugins_json.exists():
        print(f"  Plugins JSON size: {plugins_json.stat().st_size} bytes")
    
    print()
    
    # Check if dist directory exists and contents
    dist_dir = project_root / "dist" / "OBS_Installer"
    print(f"Distribution directory: {dist_dir}")
    print(f"Dist directory exists: {dist_dir.exists()}")
    
    if dist_dir.exists():
        print("Distribution contents:")
        for item in dist_dir.iterdir():
            if item.is_file():
                print(f"  - {item.name} (file, {item.stat().st_size} bytes)")
            elif item.is_dir():
                file_count = len(list(item.glob('*')))
                print(f"  - {item.name}/ (directory, {file_count} items)")
        
        # Check specifically for bundled data files
        bundled_icons = dist_dir / "icons"
        bundled_plugins = dist_dir / "plugins.json"
        
        print()
        print("Bundled data files check:")
        print(f"  Icons in dist: {bundled_icons.exists()}")
        if bundled_icons.exists():
            bundled_icon_files = list(bundled_icons.glob('*'))
            print(f"    - {len(bundled_icon_files)} icon files found")
            for icon in bundled_icon_files:
                if icon.is_file():
                    print(f"      * {icon.name}")
        
        print(f"  Plugins.json in dist: {bundled_plugins.exists()}")
        if bundled_plugins.exists():
            print(f"    - Size: {bundled_plugins.stat().st_size} bytes")
    
    print()
    
    # Provide recommendations
    print("Recommendations:")
    if not icons_dir.exists():
        print("  ❌ Create the 'icons' directory in the project root")
    elif not list(icons_dir.glob('*')):
        print("  ❌ Add icon files to the 'icons' directory")
    else:
        print("  ✅ Icons directory and files are present")
    
    if not plugins_json.exists():
        print("  ❌ Create 'plugins.json' in the project root")
    else:
        print("  ✅ plugins.json file is present")
    
    if not spec_file.exists():
        print("  ❌ Create obs_installer.spec file")
    else:
        print("  ✅ Spec file is present")
    
    print()
    
    # Show the correct datas format for PyInstaller
    print("Correct PyInstaller datas format:")
    print("  For individual files:")
    print("    ('source/file.ext', 'destination_dir')")
    print("  For directories:")
    print("    ('source/directory', 'destination_dir')")
    print()
    print("Example for this project:")
    if icons_dir.exists():
        for icon in icons_dir.glob('*'):
            if icon.is_file():
                print(f"    ('{icon}', 'icons'),")
    if plugins_json.exists():
        print(f"    ('{plugins_json}', '.'),")
    
    print("=" * 60)

if __name__ == "__main__":
    main()