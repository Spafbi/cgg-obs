# Chaotic Good Gaming OBS and plugins downloader
Downloads OBS and a standard set of plugins used by Chaotic Good Gaming (CGG). This utility downloads a [JSON file](https://cgg.spafbi.com/cgg-obs.json) which instructs the utility which packages to download and install; subsequent runs of the utility will update any downloads which may have changed. An icon for CGG OBS will be created on the user's Windows desktop.
# Usage
May be run as an executable [executable](https://github.com/spafbi/cgg-obs/releases/latest/download/setup-cgg-obs.exe), or run as a python script.
## Options
These options may be used with both the executable and python script.
```txt
usage: setup-cgg-obs.py [-h] [-t TARGET] [-d DOWNLOADS] [-v]

setup-cgg-obs.py executes the CGG OBS installation and update tool.

options:
  -h, --help            show this help message and exit
  -t TARGET, --target TARGET
                        Target installation directory
  -d DOWNLOADS, --downloads DOWNLOADS
                        Downloads directory
  -v, --verbose         Verbose logging
  ```