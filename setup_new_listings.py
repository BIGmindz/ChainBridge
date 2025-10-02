#!/usr/bin/env python3
"""
Setup script for New Listings Radar module

This script verifies and installs all necessary dependencies for the
New Listings Radar module.
"""

import subprocess
import sys

import pkg_resources

# Required packages for New Listings Radar
REQUIRED_PACKAGES = {
    "beautifulsoup4": "bs4",
    "matplotlib": "matplotlib",
    "seaborn": "seaborn",
    "pandas": "pandas",
    "ccxt": "ccxt",
    "aiohttp": "aiohttp",
    "numpy": "numpy",
    "requests": "requests",
}


def check_packages():
    """Check if required packages are installed"""
    missing = []
    installed = {}

    print("📋 Checking required packages for New Listings Radar...")

    # Get installed packages
    installed_packages = {pkg.key: pkg.version for pkg in pkg_resources.working_set}

    # Check each required package
    for package, module in REQUIRED_PACKAGES.items():
        if package.lower() in installed_packages:
            installed[package] = installed_packages[package.lower()]
            print(f"✅ {package} ({installed_packages[package.lower()]}) is installed")
        else:
            missing.append(package)  # type: ignore
            print(f"❌ {package} is NOT installed")

    return missing, installed


def install_packages(packages):
    """Install missing packages"""
    if not packages:
        print("✅ All required packages are already installed")
        return True

    print(f"📦 Installing {len(packages)} missing package(s): {', '.join(packages)}")

    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + packages)
        print("✅ All packages installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing packages: {e}")
        return False


def create_requirements_file():
    """Create or update requirements-listings.txt"""
    # Get installed versions
    installed_packages = {pkg.key: pkg.version for pkg in pkg_resources.working_set}

    with open("requirements-listings.txt", "w") as f:
        for package in REQUIRED_PACKAGES.keys():
            if package.lower() in installed_packages:
                f.write(f"{package}=={installed_packages[package.lower()]}\n")
            else:
                f.write(f"{package}\n")

    print("📄 Created requirements-listings.txt")


def main():
    """Main execution function"""
    print("🚀 Setting up New Listings Radar dependencies...")

    # Check for required packages
    missing, installed = check_packages()

    # Install missing packages
    if missing:
        success = install_packages(missing)
        if not success:
            print("⚠️ Some packages could not be installed.")
            print("Please install them manually with:")
            print(f"pip install {' '.join(missing)}")

    # Create requirements file
    create_requirements_file()

    print("\n🎯 You can install all dependencies with:")
    print("pip install -r requirements-listings.txt")

    print("\n✨ Setup complete! You can now run the New Listings Radar:")
    print("python run_new_listings_radar.py --scan")


if __name__ == "__main__":
    main()
