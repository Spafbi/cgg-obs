# Chaotic Good Gaming OBS and plugins downloader
Downloads OBS and a standard set of plugins used by Chaotic Good Gaming (CGG). This utility downloads a [JSON file](https://cgg.spafbi.com/cgg-obs.json) which instructs the utility which packages to download and install; subsequent runs of the utility will update any downloads which may have changed. An icon for CGG OBS will be created on the user's Windows desktop.
# Usage
May be run as an executable ([downloaded from here](https://github.com/spafbi/cgg-obs/releases/latest/download/setup-cgg-obs.exe)), or run as a python script.
## Options
These options may be used with both the executable and python script.
```txt
usage: setup-cgg-obs.py [-h] [-j JSON] [-t TARGET] [-d DOWNLOADS] [-b BRANDING] [-v]

setup-cgg-obs.py executes the CGG OBS installation and update tool.

options:
  -h, --help            show this help message and exit
  -j JSON, --json JSON  May be used to specify a local JSON file
  -t TARGET, --target TARGET
                        Target installation directory
  -d DOWNLOADS, --downloads DOWNLOADS
                        Downloads directory
  -b BRANDING, --branding BRANDING
                        Icon branding to use. CGG, GC, etc.
  -v, --verbose         Verbose logging
  ```
# Errors
If you run into any errors in executing this downloader/updator, reboot your PC, then close all apps which might use OBS resources such as the virtualcam (Discord, Nvidia Broadcast, and any other apps which might use the webcam).
