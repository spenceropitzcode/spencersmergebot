"""
Setup script for Live Icon Overlay

This script installs the required dependencies for the live overlay application.
"""

import subprocess
import sys

def install_package(package):
    """Install a package using pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✓ Successfully installed {package}")
        return True
    except subprocess.CalledProcessError:
        print(f"✗ Failed to install {package}")
        return False

def main():
    print("Setting up Live Icon Overlay dependencies...")
    print("=" * 50)
    
    required_packages = [
        "pyautogui>=0.9.54",
        "pillow>=8.0.0", 
        "opencv-python>=4.5.0",
        "numpy>=1.21.0"
    ]
    
    optional_packages = [
        "pywin32>=227"  # For click-through overlay on Windows
    ]
    
    print("Installing required packages...")
    success_count = 0
    for package in required_packages:
        if install_package(package):
            success_count += 1
    
    print(f"\nInstalled {success_count}/{len(required_packages)} required packages")
    
    print("\nInstalling optional packages...")
    for package in optional_packages:
        print(f"Attempting to install {package} (optional)...")
        install_package(package)
    
    print("\n" + "=" * 50)
    if success_count == len(required_packages):
        print("✓ Setup complete! You can now run the live overlay.")
        print("Run: python live_icon_overlay.py")
    else:
        print("⚠ Some packages failed to install. The overlay may not work properly.")
    
    print("\nMake sure your 'market_icons' folder is in the same directory!")

if __name__ == "__main__":
    main()
