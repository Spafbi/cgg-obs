from bs4 import BeautifulSoup
from fnmatch import fnmatch
from glob import glob
from os.path import abspath, basename, dirname
from pathlib import Path
from pprint import pprint
from win32com.client import Dispatch
import argparse
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


class cggOBS:
    def __init__(self, **kwargs):
        # Get some vars from the json_data
        self.api_key = kwargs.get("api_key")
        self.downloads = kwargs.get("downloads")
        self.downloads_directory = kwargs.get("downloads_directory")
        self.icon = kwargs.get("icon")
        self.install_log = kwargs.get("install_log")
        self.installation_directory = kwargs.get("installation_directory")
        self.moves = kwargs.get("moves", dict())

        self.makedir(self.downloads_directory)
        self.makedir(self.installation_directory)

    def makedir(self, directory):
        if not os.path.exists(directory):
            os.makedirs(directory)

    def install_from_github(self, this_object):
        # Get object details from config
        this_thing = self.downloads.get(this_object, [False, False, False])

        # Return False if object was not in the config
        if not this_thing:
            logging.debug(f"{this_object} not found in downloads configuration")
            return

        # The the github info for object downloads
        target_url, target_filename, target_tag = get_github_project_download_url(
            this_thing.get("github"), this_thing.get("filename"), self.api_key
        )

        # Exit if the installed tag matches the
        if self.install_log.get(this_object, {}).get("tag", False) == target_tag:
            logging.debug("Installed version matches latest. Skipping download.")
            return

        # Download the file and extract it
        if download_file(target_url, self.downloads_directory, target_filename, self.api_key):
            print_text(f"Downloading {this_object}...")
            directory = Path(self.installation_directory)
            file_path = Path(f"{self.downloads_directory}/{target_filename}")
            filename = f"{file_path}"
            filename_len = len(filename)
            if filename[filename_len - 3 :].lower() == "zip":
                extraction_success = extract_zip(directory, file_path)
            elif filename[filename_len - 2 :].lower() == "7z":
                extraction_success = extract_7z(directory, file_path)
            else:
                extraction_success = [False]
            # Log success
            if extraction_success[0]:
                print_text(f"Installed {this_object}")
                self.install_log[this_object] = {
                    "filename": target_filename,
                    "tag": target_tag,
                }
                return
            else:
                logging.info(f"Error installing {this_object}: {extraction_success[0]}")
        else:
            logging.info(
                f"Could not download object: {target_url}, {self.downloads_directory}, {target_filename}"
            )
        return

    def install_from_obsproject(self, this_object):
        # Get object details from config
        this_thing = self.downloads.get(this_object, [False, False, False])

        # Return False if object was not in the config
        if not this_thing:
            logging.debug(f"{this_object} not found in downloads configuration")
            return

        # The obsproject info for object downloads
        target_url, target_filename = get_obs_project_download_url(
            this_thing.get("obsproject"),
            this_thing.get("filename"),
        )

        # Exit if the installed previously installed filename matches
        has_asterisk = "*" in this_thing.get("filename")
        has_question_mark = "?" in this_thing.get("filename")
        filenames_match = (
            self.install_log.get(this_object, {}).get("filename", False)
            == target_filename
        )
        force_download = not (has_asterisk or has_question_mark)
        if filenames_match and not force_download:
            logging.debug("Installed version matches latest. Skipping download.")
            return

        # Download the file and extract it
        if download_file(target_url, self.downloads_directory, target_filename):
            print_text(f"Downloading {this_object}...")
            directory = Path(self.installation_directory)
            file_path = Path(f"{self.downloads_directory}/{target_filename}")
            filename = f"{file_path}"
            filename_len = len(filename)
            if filename[filename_len - 3 :].lower() == "zip":
                extraction_success = extract_zip(directory, file_path)
            elif filename[filename_len - 2 :].lower() == "7z":
                extraction_success = extract_7z(directory, file_path)
            else:
                extraction_success = False
            # Log success
            if extraction_success[0]:
                print_text(f"Installed {this_object}")
                self.install_log[this_object] = {"filename": target_filename}
                return
            else:
                logging.info(f"Error installing {this_object}: {extraction_success[0]}")
        else:
            logging.info(
                f"Could not download object: {target_url}, {self.downloads_directory}, {target_filename}"
            )
        return


def get_obs_project_download_url(obsproject_path, file_pattern):
    logging.debug(f"\r\nExecuting function: {inspect.stack()[0][3]}")
    logging.debug(f"  obsproject_path: {obsproject_path}")
    logging.debug(f"     file_pattern: {file_pattern}")
    page_url = f"https://obsproject.com/forum/resources/{obsproject_path}/download"
    # Fetch the webpage
    try:
        response = requests.get(page_url)
    except Exception as e:
        logging.debug(e)
        return False, False

    # If the request was successful, the status code will be 200
    if response.status_code != 200:
        logging.debug(
            f"Download URL not identified due to HTTP reponse code: {response.status_code}"
        )
        return False, False

    # Get the content of the response
    page_content = response.content

    # Create a BeautifulSoup object and specify the parser
    soup = BeautifulSoup(page_content, "html.parser")

    # Find all elements with class "contentRow-title"
    file_elements = soup.find_all(class_="contentRow-title")

    # For each element, get the text and match with the pattern
    for file_element in file_elements:
        file_name = file_element.get_text().strip()
        if fnmatch(file_name, file_pattern):
            # If the filename matches the pattern, get the download link
            download_link = file_element.find_previous(
                "a", {"class": "button--icon--download"}
            )
            if download_link is not None:
                download_url = download_link["href"]
                # Return the full download URL, not just the path
                return requests.compat.urljoin(page_url, download_url), file_name
    return False, False


def get_github_project_download_url(github_path, file_pattern, api_key=""):
    logging.debug(f"\r\nExecuting function: {inspect.stack()[0][3]}")
    logging.debug(f"   github_path: {github_path}")
    logging.debug(f"  file_pattern: {file_pattern}")
    logging.debug(f"       api_key: '{api_key}'")
    page_url = f"https://api.github.com/repos/{github_path}/releases/latest"

    headers = dict()
    if len(api_key) > 1:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    try:
        response = requests.get(page_url, headers=headers)
    except Exception as e:
        logging.debug(e)
        return False, False, False

    if response.status_code != 200:
        logging.debug(
            f"Download URL not identified due to HTTP reponse code: {response.status_code}"
        )
        return False, False, False

    json_data = response.text
    json_data = json.loads(json_data)

    for asset in json_data.get("assets", {}):
        if fnmatch(asset.get("name"), file_pattern):
            return (
                asset.get("browser_download_url"),
                asset.get("name"),
                json_data.get("tag_name"),
            )

    return False, False, False


def read_json(json_path):
    if not os.path.isfile(json_path):
        logging.debug("File not found. Returning empty dictionary.")
        return {}

    try:
        with open(json_path) as f:
            json_data = json.load(f)
    except Exception as e:
        logging.debug(e)
        logging.debug("File load error. Returning empty dictionary.")
        json_data = {}
    return json_data


def get_install_log(directory):
    logging.debug(f"\r\nExecuting function: {inspect.stack()[0][3]}")
    logging.debug(f"  directory: {directory}")
    json_path = Path(f"{directory}/install_log.json")
    return read_json(json_path)


def set_install_log(directory, log_info):
    logging.debug(f"\r\nExecuting function: {inspect.stack()[0][3]}")
    logging.debug(f"  directory: {directory}")
    json_path = Path(f"{directory}/install_log.json")
    json_object = json.dumps(log_info, indent=4)
    try:
        with open(json_path, "w") as outfile:
            outfile.write(json_object)
    except Exception as e:
        logging.debug(f"Log file write failed: {e}")


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


# Function to download a file
def download_file(url, directory, filename, api_key=""):
    logging.debug(f"\r\nExecuting function: {inspect.stack()[0][3]}")
    logging.debug(f"        url: {url}")
    logging.debug(f"  directory: {directory}")
    logging.debug(f"   filename: {filename}")

    headers = dict()
    if len(api_key) > 1:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    try:
        response = requests.get(url, headers=headers)
        with open(os.path.join(directory, filename), "wb") as f:
            f.write(response.content)
        return True
    except Exception as e:
        logging.critical(f"Failed to download {filename} from {url}")
        return False


def extract_zip(target_directory, filename):
    logging.debug(f"\r\nExecuting function: {inspect.stack()[0][3]}")
    logging.debug(f"          filename: {filename}")
    logging.debug(f"  target_directory: {target_directory}")
    try:
        with zipfile.ZipFile(filename, "r") as zip_ref:
            zip_ref.extractall(target_directory)
        return True, False
    except Exception as e:
        logging.info(f"{filename} could not be extracted to {target_directory}")
        logging.info(e)
        return False, e


def extract_7z(target_directory, filename):
    logging.debug(f"\r\nExecuting function: {inspect.stack()[0][3]}")
    logging.debug(f"          filename: {filename}")
    logging.debug(f"  target_directory: {target_directory}")
    try:
        archive = py7zr.SevenZipFile(filename, mode="r")
        archive.extractall(path=target_directory)
        archive.close()
        return True, False
    except Exception as e:
        logging.info(f"{filename} could not be extracted to {target_directory}")
        logging.info(e)
        return False, e


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


def create_shortcuts(
    installation_directory, icon_name, shortcut_name, create_desktop=True
):
    shortcut_locations = [Path(installation_directory)]

    if create_desktop:
        shortcut_locations.append(winshell.desktop())

    bin_path = Path(f"{installation_directory}/bin/64bit/obs64.exe")
    for this_shortcut_path in shortcut_locations:
        target = Dispatch("WScript.Shell").CreateShortCut(
            f"{this_shortcut_path}\\{shortcut_name}.lnk"
        )
        target.Targetpath = f"{bin_path}"
        if os.path.exists(Path(f"{installation_directory}/{icon_name}")):
            icon_location = Path(f"{installation_directory}/{icon_name}")
            target.IconLocation = f"{icon_location}"
        target.WorkingDirectory = dirname(bin_path)
        # target.ShellExecute = "runas" # This doesn't work - was to set shortcut to run as admin
        target.save()


def create_shortcut(installation_directory, icon_name):
    desktop = winshell.desktop()
    bin_path = Path(f"{installation_directory}/bin/64bit/obs64.exe")
    target = Dispatch("WScript.Shell").CreateShortCut(
        desktop + "\\Chaotic Good Gaming OBS.lnk"
    )
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
        "-j",
        "--json",
        type=str,
        required=False,
        help="""May be used to specify a local JSON file""",
        default="__invalid__",
    )
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
        "-b",
        "--branding",
        type=str,
        required=False,
        help="""Icon branding to use. CGG, GC, etc.""",
        default="CGG",
    )
    parser.add_argument(
        "-g",
        "--github",
        type=str,
        required=False,
        help="""GitHub personal access token - create one with only "public_repo" permissions at: https://github.com/settings/tokens""",
        default="",
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

    # Get installation log
    install_log = get_install_log(downloads_directory)

    # Download the JSON content from the Gist or load from local file
    json_path = Path(args.json)
    if os.path.isfile(json_path):
        try:
            with open(json_path) as f:
                json_data = json.load(f)
        except Exception as e:
            logging.debug(e)
            logging.debug("Configuration file load error. Using default configuration")
            json_data = {}
    else:
        json_dowload_info = get_github_project_download_url(
            "Spafbi/cgg-obs", "cgg-obs.json"
        )
        if json_dowload_info[0]:
            response = requests.get(json_dowload_info[0])
        else:
            logging.info(
                "Could not determine cgg-obs.json download URL for the current release. Installation halted."
            )
            exit(1)

        json_data = response.text
        json_data = json.loads(json_data)

    # Create configuration dictionary
    icon = json_data.get("branding", dict()).get(args.branding, False)
    if not icon:
        icon = json_data.get("branding", dict()).get("CGG")

    config = dict()
    data = json_data.get("downloads", dict())
    moves = json_data.get("moves", dict())
    config["api_key"] = args.github
    config["downloads"] = data
    config["downloads_directory"] = downloads_directory
    config["icon"] = icon
    config["install_log"] = install_log
    config["installation_directory"] = installation_directory
    config["moves"] = moves
    installer = cggOBS(**config)

    # Install OBS
    installer.install_from_github("OBS")

    # Iterate over the items in the JSON data
    for key, value in data.items():
        if key.lower() == "obs":
            continue
        if value.get("github", False):
            installer.install_from_github(key)
        elif value.get("obsproject", False):
            installer.install_from_obsproject(key)

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


    # Create a Desktop shortcut
    icon_url, target_filename, tag_name = get_github_project_download_url(
        icon.get("github"),
        icon.get("filename"),
        args.github
    )
    icon_path = Path(f"{installation_directory}/{target_filename}")
    shortcut_name = icon.get("shortcut_name", "Chaotic Good Gaming OBS")

    if not os.path.exists(icon_path):
        download_file(icon_url, installation_directory, target_filename, args.github)

    installer.install_log["shortcut_icon"] = {"filename": target_filename}

    create_shortcuts(installation_directory, target_filename, shortcut_name)

    # Write out install log
    set_install_log(downloads_directory, installer.install_log)


if __name__ == "__main__":
    main()
