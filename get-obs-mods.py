import json
import requests
# import logging
import os
import hashlib

gist_url = 'https://gist.githubusercontent.com/Spafbi/89c5626cc40a9fd66266b33df3b24ab9/raw/cgg-obs-mods.json'

# Function to download a file
def download_file(url, filename, directory):
    response = requests.get(url)
    with open(os.path.join(directory, filename), 'wb') as f:
        f.write(response.content)

def md5_check(filename):
    filename = "path/to/file"
    hash_md5 = hashlib.md5()

    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)

    return hash_md5.hexdigest()


# Activate logging
# logging.basicConfig(level=logging.DEBUG)

# Download the JSON content from the Gist
response = requests.get(gist_url)
json_data = response.text

# Parse the JSON string
data = json.loads(json_data)

# Iterate over the items in the JSON data
for key, value in data.items():
    # Get the download URL
    current_mod = key
    download_url = value.get('download_url', False)
    filename = value.get('filename', False)
    md5sum = value.get('md5', False)
    output_directory = value.get('directory', "plugins")
    
    if not download_url:
        continue

    # Extract the filename from the URL
    if not filename:
        filename = download_url.split("/")[-1].split("?")[0]
    
    # Create the output directory if needed
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    this_file_path = f'{filename}/{output_directory}'
    if md5sum and os.path.isfile(this_file_path):
        try:
            current_md5 = md5_check(this_file_path)
        except Exception as e:
            print(f'Could not get md5sum of {this_file_path}')
            current_md5 = False

        print(md5sum, current_md5)
        if md5sum == current_md5:
            print(f'File hash matches. Skipping download of current_mod')
            continue

    print(f'Downloading "{current_mod}" as {filename}...')
    download_file(download_url, filename, output_directory)
    print(f'{filename} downloaded successfully!')

print("All files downloaded.")