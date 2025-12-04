"""
CGG OBS Studio Installer for Windows
A Python 3.13+ application with Qt6 GUI for downloading and installing OBS Studio
"""

from setuptools import setup, find_packages

setup(
    name="obs-installer",
    version="3.0.0",
    description="CGG OBS Studio Installer for Windows with Qt6 GUI",
    author="Spafbi",
    python_requires=">=3.13",
    packages=find_packages(),
    install_requires=[
        "PyQt6>=6.6.0",
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "py7zr>=0.20.0",
        "pywin32>=306; sys_platform == 'win32'",
        "winshell>=0.6; sys_platform == 'win32'",
        "configparser>=5.3.0",
        "pyinstaller>=6.0.0",
    ],
    entry_points={
        "console_scripts": [
            "obs-installer=obs_installer.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.13",
        "Operating System :: Microsoft :: Windows",
        "Topic :: Multimedia :: Video",
        "Topic :: System :: Installation/Setup",
    ],
)