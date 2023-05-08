from glob import glob
from os.path import abspath, basename, dirname
from pathlib import Path
from win32com.client import Dispatch
import argparse
# import ctypes
import hashlib
import inspect
import json
import logging
import os
import py7zr
import requests
import shutil
import stat
import sys
import textwrap
import winshell
import zipfile

sys.path.insert(1, abspath(dirname(sys.argv[0])))

gist_url = "https://cgg.spafbi.com/cgg-obs.json"


def print_text(
    text,
    initial_indent="  ",
    subsequent_indent="  ",
    width=70,
):
    logging.debug(f"\r\nExecuting function: {inspect.stack()[0][3]}")
    logging.debug(f"               text: {text}")
    logging.debug(f"     initial_indent: {initial_indent}")
    logging.debug(f"  subsequent_indent: {subsequent_indent}")
    logging.debug(f"              width: {width}")
    wrapper = textwrap.TextWrapper(
        width=width, initial_indent=initial_indent, subsequent_indent=subsequent_indent
    )
    word_list = wrapper.wrap(text=text)
    for element in word_list:
        print(element)


def download_and_extract(
    download_name, this_object, installation_directory, download_directory=False
):
    logging.debug(f"\r\nExecuting function: {inspect.stack()[0][3]}")
    logging.debug(f"           download_name: {download_name}")
    logging.debug(f"             this_object: {this_object}")
    logging.debug(f"  installation_directory: {installation_directory}")
    logging.debug(f"      download_directory: {download_directory}")
    print("—" * 70)
    print_text(f"{download_name}", "")
    print("—" * 70)
    download_url = this_object.get("download_url", False)
    filename = this_object.get("filename", False)
    md5sum = this_object.get("md5", False)

    installation_path = Path(installation_directory)
    if not download_directory:
        download_directory_path = Path(f"{installation_directory}/downloads")
    else:
        download_directory_path = Path(f"{download_directory}")
    file_path = Path(f"{download_directory_path}/{filename}")
    file_semaphore = Path(f"{download_directory_path}/{filename}.installed")

    # Create the download directory if needed
    if not os.path.exists(download_directory_path):
        os.makedirs(download_directory_path)

    # Check to see if the file has been downloaded
    is_downloaded = os.path.isfile(file_path)

    # If the file has been downloaded compare md5 values, else set md5_matches to False
    md5_matches = md5_check(file_path, md5sum) if is_downloaded else False

    # To force a reinstallation of a package, remove the installation semaphore if the md5sum doesn't match
    if not md5_matches:
        try:
            os.remove(file_semaphore)
        except Exception as e:
            pass

    # Retrying up to three times, download the target file until the md5sum matches the expected value
    retries = 3
    while (not md5_matches) and (retries > 0):
        print_text(f"File not yet downloaded or md5sum check failed")
        print_text(f"Downloading {download_name}")
        download_file(download_url, download_directory_path, filename)
        md5_matches = md5_check(file_path, md5sum)
        retries -= 1

    # Exit if the md5 values don't match by this point.
    if not md5_matches:
        print_text("Downloaded file does not match expected checksum value")
        print_text(
            f"Download of {download_name} failed. {download_name} has not been installed"
        )
        print()
        return

    is_installed = os.path.isfile(file_semaphore) if md5_matches else False

    if md5_matches and not is_installed:
        print_text(f"Installing {download_name}")
        filename_len = len(filename)
        if filename[filename_len - 3 :].lower() == "zip":
            installed = extract_zip(installation_path, file_path)
        elif filename[filename_len - 2 :].lower() == "7z":
            installed = extract_7z(installation_path, file_path)
        else:
            installed = False

        if not installed:
            print_text(f"Installation of {download_name} failed")
        else:
            f = open(file_semaphore, "a")
            f.close()
    else:
        print_text(f"{download_name} already installed/updated")
    print()


# Function to download a file
def download_file(url, directory, filename):
    logging.debug(f"\r\nExecuting function: {inspect.stack()[0][3]}")
    logging.debug(f"        url: {url}")
    logging.debug(f"  directory: {directory}")
    logging.debug(f"   filename: {filename}")
    try:
        response = requests.get(url)
        with open(os.path.join(directory, filename), "wb") as f:
            f.write(response.content)
        return True
    except Exception as e:
        logging.critical(f"Failed to download {filename} from {url}")
        return False


def md5_check(filename, expected_hash):
    logging.debug(f"\r\nExecuting function: {inspect.stack()[0][3]}")
    logging.debug(f"       filename: {filename}")
    logging.debug(f"  expected_hash: {expected_hash}")
    filename = Path(filename)
    hash_md5 = hashlib.md5()

    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)

    if hash_md5.hexdigest() == expected_hash:
        return True

    return False


def extract_zip(target_directory, filename):
    logging.debug(f"\r\nExecuting function: {inspect.stack()[0][3]}")
    logging.debug(f"          filename: {filename}")
    logging.debug(f"  target_directory: {target_directory}")
    try:
        with zipfile.ZipFile(filename, "r") as zip_ref:
            zip_ref.extractall(target_directory)
        return True
    except Exception as e:
        logging.debug(f"{filename} could not be extracted to {target_directory}")
        logging.debug(e)
        return False


def extract_7z(target_directory, filename):
    logging.debug(f"\r\nExecuting function: {inspect.stack()[0][3]}")
    logging.debug(f"          filename: {filename}")
    logging.debug(f"  target_directory: {target_directory}")
    try:
        archive = py7zr.SevenZipFile(filename, mode="r")
        archive.extractall(path=target_directory)
        archive.close()
        return True
    except Exception as e:
        logging.debug(f"{filename} could not be extracted to {target_directory}")
        logging.debug(e)
        return False


def move_and_remove_directory(source, destination):
    logging.debug(f"\r\nExecuting function: {inspect.stack()[0][3]}")
    logging.debug(f"       source: {source}")
    logging.debug(f"  destination: {destination}")
    try:
        move_directory(source, destination)
    except:
        return

    # Delete the directory
    os.chmod(source, stat.S_IWRITE)
    os.rmdir(source)


def move_directory(source, destination):
    logging.debug(f"\r\nExecuting function: {inspect.stack()[0][3]}")
    logging.debug(f"       source: {source}")
    logging.debug(f"  destination: {destination}")
    if not os.path.exists(source):
        return
    # Iterate through the items in the source directory
    for item in os.listdir(source):
        # Construct the full paths for the source and destination items
        source_item = os.path.join(source, item)
        destination_item = os.path.join(destination, item)

        os.chmod(source_item, stat.S_IWRITE)
        # Check if the current item is a directory
        if os.path.isdir(source_item):
            # If the destination directory does not exist, create it
            if not os.path.exists(destination_item):
                os.makedirs(destination_item)
            # Recursively move the contents of the current subdirectory
            move_directory(source_item, destination_item)
            # Remove the now-empty source subdirectory
            os.rmdir(source_item)
        else:
            # Move the item to the destination directory
            shutil.move(source_item, destination_item)


def create_shortcut(installation_directory, icon_name):
    desktop = winshell.desktop()
    bin_path = Path(f"{installation_directory}/bin/64bit/obs64.exe")
    target = Dispatch("WScript.Shell").CreateShortCut(desktop + "\\Chaotic Good Gaming OBS.lnk")
    target.Targetpath = f"{bin_path}"
    if os.path.exists(Path(f"{installation_directory}/{icon_name}")):
        icon_location = Path(f"{installation_directory}/{icon_name}")
        target.IconLocation = f"{icon_location}"
    target.WorkingDirectory = dirname(bin_path)
    # target.ShellExecute = "runas" # This doesn't work - was to set shortcut to run as admin
    target.save()

def main():
    """
    Summary: Default method if this modules is run as __main__.
    """

    # Grab our user's profile
    user_profile = os.environ.get("USERPROFILE")
    installation_default = f"{user_profile}/cgg-obs"

    # Just grabbing this script's filename
    prog = basename(__file__)
    description = f"{prog} executes the CGG OBS installation and update tool."

    # Set up argparse to help people use this as a CLI utility
    parser = argparse.ArgumentParser(prog=prog, description=description)

    parser.add_argument(
        "-t",
        "--target",
        type=str,
        required=False,
        help="""Target installation directory""",
        default=installation_default,
    )
    parser.add_argument(
        "-d",
        "--downloads",
        type=str,
        required=False,
        help="""Downloads directory""",
        default="__invalid__",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        required=False,
        help="""Verbose logging""",
    )

    # Parse our arguments!
    args = parser.parse_args()

    installation_directory = args.target
    if args.downloads == "__invalid__":
        downloads_directory = f"{installation_directory}/downloads"
    else:
        downloads_directory = f"{args.downloads}"

    # This just grabs our script's path for reuse
    script_path = os.path.abspath(os.path.dirname(sys.argv[0]))

    # Check for files to trigger debug logging
    verbose = True if len(glob(str(Path(f"{script_path}/debug*")))) else False

    # Enable either INFO or DEBUG logging
    cgg_obs_logger = logging.getLogger()
    output_file_handler = logging.FileHandler("setup.log")
    stdout_handler = logging.StreamHandler(sys.stdout)
    cgg_obs_logger.addHandler(output_file_handler)
    cgg_obs_logger.addHandler(stdout_handler)
    if verbose or args.verbose:
        cgg_obs_logger.setLevel(logging.DEBUG)
    else:
        cgg_obs_logger.setLevel(logging.INFO)

    # Download the JSON content from the Gist
    response = requests.get(gist_url)
    json_data = response.text

    # Parse the JSON string
    gist_data = json.loads(json_data)
    data = gist_data.get("downloads", dict())
    icon = gist_data.get("icon", dict())
    moves = gist_data.get("moves", dict())

    # Let's first download and extract OBS
    this_obs = data.get("OBS", False)
    if this_obs:
        download_and_extract(
            "OBS", this_obs, installation_directory, downloads_directory
        )

    # Iterate over the items in the JSON data
    for key, value in data.items():
        if key.lower() == "obs":
            continue
        download_and_extract(key, value, installation_directory, downloads_directory)

    for key, value in moves.items():
        source = Path(f"{installation_directory}/{value}")
        destination = Path(f"{installation_directory}")
        if not os.path.exists(source):
            continue
        print("—" * 70)
        print_text(f"Moving files for {key}", "")
        print_text(f"from: {source}")
        print_text(f"  to: {destination}")
        move_and_remove_directory(source, destination)
        print("—" * 70)

    icon_filename = icon.get("filename", "cgg-rotated-logo.ico")
    icon_url = icon.get("download_url", "https://cgg.spafbi.com/cgg-rotated-logo.ico")
    icon_path = Path(f"{installation_directory}/{icon_filename}")
    if not os.path.exists(icon_path):
        download_file(icon_url, installation_directory, icon_filename)

    create_shortcut(installation_directory, icon_filename)


if __name__ == "__main__":
    main()
