from bs4 import BeautifulSoup
from collections import defaultdict
from datetime import datetime
from fnmatch import fnmatch
from glob import glob
from os.path import basename, dirname
from pathlib import Path
from win32com.client import Dispatch
import argparse
import inspect
import json
import logging
import os
import py7zr
import requests
import shutil
import sys
import winshell
import zipfile


class cggOBS:
    def __init__(self, **kwargs):
        logging.debug(f"...")
        logging.debug(f"Executing function: {inspect.stack()[0][3]}")
        for name, value in kwargs.items():
            logging.debug(f"  {name}: {value}")

        downloads = kwargs.get("downloads")
        self.branding = kwargs.get("branding")
        self.github_api = kwargs.get("github_api_key")
        self.installation_directory = Path(kwargs.get("target"))
        self.downloads_directory = self.define_downloads_dir(downloads)
        self.obs_binary = f"{self.installation_directory}/bin/64bit/obs64.exe"
        # create a file name with the current date and time
        self.date_str = datetime.now().strftime("%Y%m%d%H%M%S")

        # Track our downloads
        self.downloads_status = defaultdict(lambda: defaultdict(dict))

        # Set our versions tracking file name and load it
        self.installed_versions_file = Path(f"{self.downloads_directory}/versions.json")
        self.installed_versions = read_json_file(self.installed_versions_file)

        # load our config file
        self.json_data = self.load_obs_json(kwargs.get("json_file", "__invalid__"))

        # define our icon into
        self.define_icon()

    def define_downloads_dir(self, downloads):
        # Set our downloads directory
        logging.debug(f"...")
        logging.debug(f"Executing function: {inspect.stack()[0][3]}")
        for name, value in locals().items():
            logging.debug(f"  {name}: {value}")

        if downloads == "__invalid__":
            return Path(f"{self.installation_directory}/downloads")
        else:
            return Path(downloads)

    def define_icon(self):
        # Define our icon info
        logging.debug(f"...")
        logging.debug(f"Executing function: {inspect.stack()[0][3]}")
        for name, value in locals().items():
            logging.debug(f"  {name}: {value}")

        # This is what we'll use for defaults
        default_branding_info = {
            "filename": "cgg-rotated-logo.ico",
            "github": "Spafbi/cgg-obs",
            "shortcut_name": "Chaotic Good Gaming OBS",
        }

        # Get the values from our config
        config_branding_info = self.json_data.get("branding", dict())
        branding_info = config_branding_info.get(
            self.branding.upper(), default_branding_info
        )

        # Set our icon info for use elsewhere in this object
        self.github_path = branding_info.get("github", "Spafbi/cgg-obs")
        self.icon_filename = branding_info.get("filename", "cgg-rotated-logo.ico")
        self.icon_url = f"https://raw.githubusercontent.com/{self.github_path}/main/icons/{self.icon_filename}"
        self.shortcut_icon_filename = (
            f"{self.installation_directory}/{self.icon_filename}"
        )
        self.shortcut_name = branding_info.get(
            "shortcut_name", "Chaotic Good Gaming OBS"
        )

    def download_icon(self):
        # Dowload the icon for the Desktop icon
        logging.debug(f"...")
        logging.debug(f"Executing function: {inspect.stack()[0][3]}")
        for name, value in locals().items():
            logging.debug(f"  {name}: {value}")

        # Set our download dictionary
        download_this = {
            "output_directory": self.installation_directory,
            "output_filename": self.icon_filename,
            "url": self.icon_url,
        }

        download_file(**download_this)

    def download_objects(self):
        # Download objects as defined in the config
        logging.debug(f"...")
        logging.debug(f"Executing function: {inspect.stack()[0][3]}")
        for name, value in locals().items():
            logging.debug(f"  {name}: {value}")

        # Iterate through the download objects
        for this_object, values in self.json_data.get(
            "downloads", defaultdict(lambda: defaultdict(dict))
        ).items():
            filename_pattern = values.get("filename", False)
            force_download = values.get("force_download", False)
            if not filename_pattern:
                continue

            tag = None

            if "obsproject" in values:
                this_url, filename = get_obs_project_download_url(
                    values.get("obsproject"), filename_pattern
                )
            elif "github" in values:
                this_url, filename, tag = get_github_project_download_url(
                    values.get("github"), filename_pattern, self.github_api
                )
                logging.debug(this_url)
                logging.debug(filename)
                logging.debug(tag)
            else:  # Let's possibly put direct downloads here at a future update
                continue

            download_this = {
                "output_directory": self.downloads_directory,
                "output_filename": filename,
                "url": this_url,
            }

            if "github" in values:
                download_this["api_key"] = self.github_api

            installed_versions_object = self.installed_versions.get(
                this_object, defaultdict(lambda: defaultdict(dict))
            )
            installed_version = installed_versions_object.get("filename", False)
            installed_tag = installed_versions_object.get("tag", False)

            installed_matches = installed_version == filename
            static_name = not ("?" in filename_pattern or "*" in filename_pattern)

            if tag == None:
                tags_match = True
            elif tag == installed_tag:
                tags_match = True
            else:
                tags_match = False

            download = False
            if not tags_match:
                download = True
            elif not installed_matches:
                download = True
            elif force_download:
                download = True

            if not download:
                continue

            success = download_file(**download_this)

            self.downloads_status[this_object]["download_success"] = success
            self.downloads_status[this_object]["filename"] = filename

            if success and "github" in values:
                self.downloads_status[this_object]["tag"] = tag

    def install_downloads(self, single_target=False):
        # Install our downloaded items
        logging.debug(f"...")
        logging.debug(f"Executing function: {inspect.stack()[0][3]}")
        for name, value in locals().items():
            logging.debug(f"  {name}: {value}")

        for download_object, values in self.downloads_status.items():
            if not values.get("download_success", False):
                continue
            if single_target and download_object != single_target:
                continue
            if not single_target and download_object.lower() == "obs":
                continue

            del self.downloads_status[download_object]["download_success"]

            filename = values.get("filename")
            tag = values.get("tag", False)
            file_path = Path(f"{self.downloads_directory}/{filename}")
            filename_len = len(filename)
            if filename[filename_len - 3 :].lower() == "zip":
                extraction_success = extract_zip(file_path, self.installation_directory)
            elif filename[filename_len - 2 :].lower() == "7z":
                extraction_success = extract_7z(file_path, self.installation_directory)
            else:
                self.downloads_status[download_object]["installed"] = False
                extraction_success = False

            if extraction_success:
                self.installed_versions[download_object]["filename"] = filename
                self.downloads_status[download_object]["installed"] = True
                if tag:
                    self.installed_versions[download_object]["tag"] = tag

    def load_obs_json(self, file_name):
        # Load the JSON from multiple possible sources
        logging.debug(f"...")
        logging.debug(f"Executing function: {inspect.stack()[0][3]}")
        for name, value in locals().items():
            logging.debug(f"  {name}: {value}")

        result = defaultdict(lambda: defaultdict(dict))
        if os.path.exists(file_name):  # read a local file
            result = read_json_file(file_name)
        elif file_name.startswith("http://") or file_name.startswith(
            "https://"
        ):  # read from URL
            result = read_json_from_url(file_name)
        elif file_name != "__invalid__":  # try reading from URL
            result = read_json_from_url(f"http://{file_name}")

        if (
            not len(result) or file_name == "__invalid__"
        ):  # Use a default config if we have an empty result or no file was specified.
            url = f"https://raw.githubusercontent.com/Spafbi/cgg-obs/main/defaults.json"
            result = read_json_from_url(url)
        return result

    def move_directories(self):
        # Some plugins down't extract cleanly - we fix that, here.
        logging.debug(f"...")
        logging.debug(f"Executing function: {inspect.stack()[0][3]}")
        for name, value in locals().items():
            logging.debug(f"  {name}: {value}")
        moves = self.json_data.get("moves", dict())
        for key, value in moves.items():
            if not key in self.downloads_status:
                continue
            source = str(Path(f"{self.installation_directory}/{value}"))
            target = str(Path(f"{self.installation_directory}"))
            copy_directory_contents(source, target)

            try:
                shutil.rmtree(source)
                logging.debug(f"Directory {source} removed successfully.")
            except OSError as e:
                logging.debug(f"Error occurred during removal of {source}: {e}")

    def write_download_status(self):
        # Save some download info for troubleshooting
        logging.debug(f"...")
        logging.debug(f"Executing function: {inspect.stack()[0][3]}")
        for name, value in locals().items():
            logging.debug(f"  {name}: {value}")

        if not self.downloads_status:
            return
        file_name = Path(f"{self.downloads_directory}/downloads_{self.date_str}.log")
        write_dict_to_file(self.downloads_status, file_name)

    def write_installed_versions(self):
        # Record our installed versions
        logging.debug(f"...")
        logging.debug(f"Executing function: {inspect.stack()[0][3]}")
        for name, value in locals().items():
            logging.debug(f"  {name}: {value}")

        if not self.installed_versions:
            return
        write_dict_to_file(self.installed_versions, self.installed_versions_file)


def configure_logging(debug_mode):
    # set the log level based on the debug_mode argument
    logging.debug(f"...")
    logging.debug(f"Executing function: {inspect.stack()[0][3]}")
    for name, value in locals().items():
        logging.debug(f"  {name}: {value}")

    if debug_mode:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    # create a file name with the current date and time
    date_str = datetime.now().strftime("%Y%m%d%H%M%S")
    log_file_name = f"setup_{date_str}.log"

    # set up the logger
    logger = logging.getLogger("")
    logger.setLevel(log_level)

    # create a file handler that writes to the log file
    try:
        file_handler = logging.FileHandler(log_file_name)
    except IOError as e:
        logger.error("Could not open log file: %s" % e)
        return False

    # create a formatter and add it to the handler
    formatter = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")
    file_handler.setFormatter(formatter)

    # add the handler to the logger
    logger.addHandler(file_handler)

    return True


def create_shortcut(**kwargs):
    """
    Create a Windows application shortcut on the user's desktop.
    """
    logging.debug(f"...")
    logging.debug(f"Executing function: {inspect.stack()[0][3]}")
    for name, value in kwargs.items():
        logging.debug(f"  {name}: {value}")

    bin_path = kwargs.get("binary_path")
    icon_path = kwargs.get("icon_path")
    shortcut_name = kwargs.get("shortcut_name")
    logging.debug(f"...")
    logging.debug(f"Executing function: {inspect.stack()[0][3]}")
    for name, value in locals().items():
        logging.debug(f"  {name}: {value}")

    try:
        # Get the path to the user's desktop
        desktop = winshell.desktop()

        # Create a path for the shortcut to be saved
        path = os.path.join(desktop, shortcut_name + ".lnk")

        # Create a new shortcut object
        shortcut = Dispatch("WScript.Shell").CreateShortCut(path)

        # Set the shortcut properties
        shortcut.Targetpath = bin_path
        shortcut.IconLocation = icon_path
        shortcut.WorkingDirectory = dirname(bin_path)
        shortcut.save()

        # Logging success message
        logging.info(f"Desktop shortcut {shortcut_name} created successfully!")

    except Exception as ex:
        # Logging error message
        logging.info(f"Desktop shortcut creation failed: {ex}")


def download_file(**kwargs):
    """
    Downloads a file from a given URL and saves it to a specified directory with a specified filename.
    An optional API key can be passed in to use in an authorization bearer header.
    """
    logging.debug(f"...")
    logging.debug(f"Executing function: {inspect.stack()[0][3]}")
    for name, value in kwargs.items():
        logging.debug(f"  {name}: {value}")

    github_api_key = kwargs.get("github_api_key", None)
    output_directory = kwargs.get("output_directory")
    output_filename = kwargs.get("output_filename")
    url = kwargs.get("url")
    try:
        # log input values using logging module
        logging.debug(f"...")
        logging.debug(f"Executing function: {inspect.stack()[0][3]}")
        for name, value in locals().items():
            logging.debug(f"  {name}: {value}")

        headers = defaultdict(lambda: defaultdict(dict))
        if github_api_key:
            headers = {
                "Authorization": f"Bearer {github_api_key}",
                "X-GitHub-Api-Version": "2022-11-28",
            }

        # Download file from URL
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            logging.debug(
                f"Download URL not downloaded due to HTTP reponse code: {response.status_code}"
            )
            return False

        # Save file to specified directory with specified filename
        filepath = os.path.join(output_directory, output_filename)
        with open(filepath, "wb") as file:
            file.write(response.content)

        logging.info(f"{output_filename} downloaded successfully!")
        return True

    except Exception as e:
        logging.info(f"Error occurred while downloading {output_filename}: {e}")
        logging.error(f"Error occurred while downloading {output_filename}: {e}")
        return False


def download_json(url):
    # Download a JSON file and return it as a dictionary
    logging.debug(f"...")
    logging.debug(f"Executing function: {inspect.stack()[0][3]}")
    for name, value in locals().items():
        logging.debug(f"  {name}: {value}")

    try:
        response = requests.get(url)
    except Exception as e:
        logging.info(
            "Could not download URL. Installation halted."
        )
        logging.info(e)
        exit(1)

    json_data = response.text
    return json.loads(json_data)


def extract_zip(zip_filepath, extraction_directory):
    """
    Extracts the contents of a zip file to a target extraction directory.

    :param zip_filepath: The file path of the zip file to extract.
    :type zip_filepath: str
    :param extraction_directory: The file path of the directory to extract the zip to.
    :type extraction_directory: str
    """
    logging.debug(f"...")
    logging.debug(f"Executing function: {inspect.stack()[0][3]}")
    for name, value in locals().items():
        logging.debug(f"  {name}: {value}")

    try:
        # Check if zip file exists
        if not os.path.exists(zip_filepath):
            raise FileNotFoundError(f"Zip file not found at {zip_filepath}")

        # Check if extraction directory exists, create it if not
        if not os.path.exists(extraction_directory):
            os.makedirs(extraction_directory)

        # Extract contents of zip file to extraction directory
        with zipfile.ZipFile(zip_filepath, "r") as zip:
            zip.extractall(path=extraction_directory)

        logging.info(f"Successfully extracted zip file to {extraction_directory}")
        return True

    except Exception as e:
        logging.info(f"Error occurred while extracting zip file {zip_filepath}: {e}")
        return False


def extract_7z(archive_filepath, extraction_directory):
    """
    Extracts the contents of a 7z archive file to a target extraction directory
    using py7zr.

    :param archive_filepath: The file path of the 7z archive file to extract.
    :type archive_filepath: str
    :param extraction_directory: The file path of the directory to extract the 7z archive to.
    :type extraction_directory: str
    """
    logging.debug(f"...")
    logging.debug(f"Executing function: {inspect.stack()[0][3]}")
    for name, value in locals().items():
        logging.debug(f"  {name}: {value}")

    try:
        # Check if archive file exists
        if not os.path.exists(archive_filepath):
            raise FileNotFoundError(f"Archive file not found at {archive_filepath}")

        # Check if extraction directory exists, create it if not
        if not os.path.exists(extraction_directory):
            os.makedirs(extraction_directory)

        # Extract contents of archive file to extraction directory
        with py7zr.SevenZipFile(archive_filepath, mode="r") as archive:
            archive.extractall(path=extraction_directory)
        logging.info(f"Successfully extracted 7z archive to {extraction_directory}")
        return True

    except Exception as e:
        logging.info(
            f"Error occurred while extracting 7z archive {archive_filepath}: {e}"
        )
        return False


def get_github_project_download_url(github_path, file_pattern, api_key=""):
    logging.debug(f"...")
    logging.debug(f"Executing function: {inspect.stack()[0][3]}")
    for name, value in locals().items():
        logging.debug(f"  {name}: {value}")

    page_url = f"https://api.github.com/repos/{github_path}/releases"

    headers = defaultdict(lambda: defaultdict(dict))
    if len(api_key) > 1:
        headers = {
            "Accept": "application/vnd.github+json",
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
    json_data = json.loads(json_data)[0]

    for asset in json_data.get("assets", dict()):
        if fnmatch(asset.get("name"), file_pattern):
            return (
                asset.get("browser_download_url"),
                asset.get("name"),
                json_data.get("tag_name"),
            )

    return False, False, False


def get_obs_project_download_url(obsproject_path, file_pattern):
    logging.debug(f"...")
    logging.debug(f"Executing function: {inspect.stack()[0][3]}")
    for name, value in locals().items():
        logging.debug(f"  {name}: {value}")

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


def make_dir(directory):
    """
    Moves a directory from src_dir to dest_dir.
    """
    logging.debug(f"...")
    logging.debug(f"Executing function: {inspect.stack()[0][3]}")
    for name, value in locals().items():
        logging.debug(f"  {name}: {value}")

    if not os.path.exists(directory):
        os.makedirs(directory)


def copy_directory_contents(source_dir, destination_dir):
    # Move the contents of one directory to another
    logging.debug(f"...")
    logging.debug(f"Executing function: {inspect.stack()[0][3]}")
    for name, value in locals().items():
        logging.debug(f"  {name}: {value}")

    source_dir = str(Path(source_dir))
    destination_dir = str(Path(destination_dir))
    # Check if source directory exists
    if not os.path.exists(source_dir):
        logging.debug("Source directory does not exist.")
        return

    # Check if destination directory exists, if not create it
    if not os.path.exists(destination_dir):
        try:
            os.makedirs(destination_dir)
        except OSError:
            logging.debug("Error creating destination directory.")
            return

    # Get a list of all files and directories in the source directory
    try:
        for item in os.listdir(source_dir):
            # Get the full path of the item
            item_path = os.path.join(source_dir, item)

            # Check if it is a file
            if os.path.isfile(item_path):
                # Copy the file to the destination directory
                try:
                    shutil.copy(item_path, destination_dir)
                except shutil.Error as e:
                    logging.debug(f"Failed to copy file: {item_path}. Error: {e}")
            else:
                # Recursively copy the directory to the destination directory
                destination_subdir = os.path.join(destination_dir, item)
                copy_directory_contents(item_path, destination_subdir)

        logging.debug("Contents copied successfully.")
    except OSError as e:
        logging.debug(f"Error accessing source directory: {e}")

    # Delete the directory
    # os.chmod(source_dir, stat.S_IWRITE)
    # os.rmdir(source_dir)


def read_file_line(filename, line_number=1):
    # If a file can be read, return the specified line of a file's contents. Return False if it cannot be read or the line number isn't found.
    logging.debug(f"...")
    logging.debug(f"Executing function: {inspect.stack()[0][3]}")
    for name, value in locals().items():
        logging.debug(f"  {name}: {value}")

    try:
        with open(filename, "r") as f:
            for i, line in enumerate(f, start=1):
                if i == line_number:
                    return line
    except FileNotFoundError:
        logging.info(f'File "{filename}" not found.')
    except Exception as e:
        logging.error(f"{e}")
    return False


def read_json_file(filename):
    # read a JSON file
    logging.debug(f"...")
    logging.debug(f"Executing function: {inspect.stack()[0][3]}")
    for name, value in locals().items():
        logging.debug(f"  {name}: {value}")

    try:
        with open(filename) as f:
            data = json.load(f)
            return data
    except FileNotFoundError:
        logging.info(f"The file '{filename}' does not exist.")
    except json.JSONDecodeError:
        logging.info(f"'{filename}' does not contain valid JSON.")
    logging.info("Returning empty dictionary.")
    return defaultdict(lambda: defaultdict(dict))


def read_json_from_url(url):
    # read JSON from a URL:
    logging.debug(f"...")
    logging.debug(f"Executing function: {inspect.stack()[0][3]}")
    for name, value in locals().items():
        logging.debug(f"  {name}: {value}")

    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = json.loads(response.text)
            return data
        else:
            return defaultdict(lambda: defaultdict(dict))

    except Exception as e:
        logging.debug(f"An error occurred: {e}")
        return defaultdict(lambda: defaultdict(dict))


def write_dict_to_file(dictionary, file_path):
    """
    Writes a dictionary to a JSON file.

    :param dictionary: The dictionary to write to the file.
    :type dictionary: dict
    :param file_path: The file path of the JSON file.
    :type file_path: str
    :raises FileNotFoundError: If the file path directory does not exist.
    :raises FileExistsError: If the file path already exists as a file.
    :raises IOError: If there was a problem writing the file.
    """
    logging.debug(f"...")
    logging.debug(f"Executing function: {inspect.stack()[0][3]}")
    for name, value in locals().items():
        logging.debug(f"  {name}: {value}")

    try:
        # Check if file path directory exists
        directory_path = os.path.dirname(file_path)
        if not os.path.exists(directory_path):
            raise FileNotFoundError(f"Directory not found at {directory_path}")

        # # Check if file path exists as a file
        # if os.path.isfile(file_path):
        #     raise FileExistsError(f"File already exists at {file_path}")

        # Write dictionary to file
        with open(file_path, "w") as f:
            json.dump(dictionary, f, indent=4, sort_keys=True)
        logging.debug(f"Successfully wrote dictionary to JSON file at {file_path}")
    except FileNotFoundError as e:
        logging.info(f"Error occurred: {e}")
    except FileExistsError as e:
        logging.info(f"Error occurred: {e}")
    except IOError as e:
        logging.info(f"Error occurred while writing JSON file: {e}")


# The "main" method
def main():
    """
    Summary: Default method if this modules is run as __main__.
    """
    logging.debug(f"...")
    logging.debug(f"Executing function: {inspect.stack()[0][3]}")
    for name, value in locals().items():
        logging.debug(f"  {name}: {value}")

    # This just grabs our script's path for reuse
    script_path = os.path.abspath(os.path.dirname(sys.argv[0]))

    # Grab our user's profile
    user_profile = os.environ.get("USERPROFILE")
    installation_default = Path(f"{user_profile}/cgg-obs")

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
        help="""May be used to specify an alternative JSON file""",
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

    # Check for files used to trigger debug logging, or use args.verbose setting
    verbose = (
        True
        if len(glob(str(Path(f"{script_path}/{debug_filename_pattern}"))))
        else args.verbose
    )

    # configure logging
    configure_logging(verbose)

    # Read the github API from file if it exists
    github_api_file_contents = read_file_line(
        Path(f"{script_path}/{github_api_text_filename}")
    )
    github_api_key = (
        github_api_file_contents if github_api_file_contents else args.github
    )

    config = {
        "branding": args.branding,
        "downloads": args.downloads,
        "github_api_key": github_api_key,
        "github_config_file": github_config_file,
        "github_project": github_project,
        "json_file": args.json,
        "target": args.target,
    }

    this_obs_install = cggOBS(**config)

    variables = vars(this_obs_install)
    for name, value in variables.items():
        logging.debug(f"  {name}: {value}")

    make_dir(this_obs_install.installation_directory)
    make_dir(this_obs_install.downloads_directory)

    this_obs_install.download_objects()
    this_obs_install.write_download_status()
    this_obs_install.install_downloads("OBS")
    this_obs_install.install_downloads()
    this_obs_install.write_installed_versions()
    this_obs_install.move_directories()
    this_obs_install.download_icon()

    # create a shortcut
    shortcut = {
        "binary_path": str(Path(this_obs_install.obs_binary)),
        "icon_path": str(Path(this_obs_install.shortcut_icon_filename)),
        "shortcut_name": this_obs_install.shortcut_name,
    }
    create_shortcut(**shortcut)


# A default method which executes 'main'
if __name__ == "__main__":
    # Defaults not defined by argparse are defined here for ease of future maintenance
    debug_filename_pattern = "debug*"
    github_api_text_filename = "github_api.txt"
    github_config_file = "defaults.json"
    github_project = "Spafbi/cgg-obs"

    main()
