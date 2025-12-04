#!/usr/bin/env python3
"""
Test script to check the actual size of the CGG logo icon.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_icon_properties():
    """Check the actual properties of the CGG logo icon."""
    try:
        icon_path = project_root / "icons" / "cgg-rotated-logo.ico"
        
        if icon_path.exists():
            print(f"Icon file: {icon_path}")
            print(f"File size: {icon_path.stat().st_size} bytes")
            
            # Try to get image dimensions if possible
            try:
                from PyQt6.QtGui import QPixmap
                
                pixmap = QPixmap(str(icon_path))
                if not pixmap.isNull():
                    print(f"Image dimensions: {pixmap.width()} x {pixmap.height()} pixels")
                    print(f"Image depth: {pixmap.depth()} bits")
                    
                    # Recommend scaling approach
                    if pixmap.width() <= 90 and pixmap.height() <= 90:
                        print("✓ Icon is already small enough - should display without scaling")
                    else:
                        print("✓ Icon is large - will need scaling for display")
                        
                    # Check if it's a typical icon size
                    common_sizes = [16, 24, 32, 48, 64, 96, 128, 256]
                    if pixmap.width() in common_sizes or pixmap.height() in common_sizes:
                        print(f"✓ Icon uses standard size ({pixmap.width()}x{pixmap.height()})")
                    else:
                        print(f"ℹ Icon uses non-standard size ({pixmap.width()}x{pixmap.height()})")
                        
                else:
                    print("✗ Could not load the icon as a pixmap")
                    
            except ImportError:
                print("PyQt6 not available for dimension checking")
                
        else:
            print(f"✗ Icon file not found: {icon_path}")
            
    except Exception as e:
        print(f"✗ Error checking icon properties: {e}")

def main():
    """Main function."""
    print("Checking CGG Logo Icon Properties...")
    print("=" * 50)
    check_icon_properties()
    
    print("\n" + "=" * 50)
    print("Icon display improvements:")
    print("- Only scale icons if they're significantly larger than display size")
    print("- Use original size for appropriately-sized icons")
    print("- Added padding around icon for better appearance")
    print("- Disabled automatic Qt scaling that can cause blur")

if __name__ == "__main__":
    main()