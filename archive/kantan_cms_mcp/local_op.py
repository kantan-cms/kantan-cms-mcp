import os
import zipfile
import tempfile
import requests
from .server import mcp


def get_env_vars() -> tuple[str, str]:
    """Get the value of an environment variable."""
    project_id = os.environ.get("PROJECT_ID")
    api_key = os.environ.get("CMS_API_KEY")
    return project_id, api_key


def get_env_dict(defult_project_id: str | None = None, default_api_key: str | None = None) -> dict:
    """Get environment variables as a dictionary."""
    project_id, api_key = get_env_vars()
    env_dict = {
        "PROJECT_ID": defult_project_id if defult_project_id is not None else project_id,
        "CMS_API_KEY": default_api_key if default_api_key is not None else api_key,
    }
    return env_dict


def download_zip_file(url: str) -> tuple[str, list]:
    """
    Download a zip file from a URL.
    
    Args:
        url (str): The URL to download the zip file from.
        
    Returns:
        tuple: A tuple containing the path to the downloaded zip file and a list of status messages.
    """
    results = []
    zip_path = os.path.join(tempfile.gettempdir(), "website-base.zip")
    
    results.append(f"Downloading from {url}...")
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    with open(zip_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    results.append("Download completed successfully.")
    
    return zip_path, results


def extract_zip_file(zip_path: str, extract_path: str) -> list:
    """
    Extract a zip file to a specified directory.
    Special handling:
    - Moves README.md to scripts/ directory
    - Ignores .gitignore file
    
    Args:
        zip_path (str): The path to the zip file.
        extract_path (str): The path to extract the zip file to.
        
    Returns:
        list: A list of status messages.
    """
    results = []
    results.append(f"Extracting to {extract_path}...")
    
    # Create scripts directory if it doesn't exist
    scripts_dir = os.path.join(extract_path, "scripts")
    if not os.path.exists(scripts_dir):
        os.makedirs(scripts_dir)
        results.append(f"Created scripts directory at {scripts_dir}")
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        # Get list of files in the zip
        file_list = zip_ref.namelist()
        
        for file_path in file_list:
            # Get the filename from the path
            filename = os.path.basename(file_path)
            
            # Skip .gitignore files
            if filename == ".gitignore":
                results.append(f"Skipping {filename}")
                continue
                
            # Handle README.md - extract to scripts/ directory
            if filename == "README.md":
                # Extract README.md to scripts/ directory
                source = zip_ref.open(file_path)
                target_path = os.path.join(scripts_dir, filename)
                target = open(target_path, "wb")
                with source, target:
                    target.write(source.read())
                results.append(f"Moved {filename} to scripts/ directory")
            else:
                # Extract all other files normally
                zip_ref.extract(file_path, extract_path)
    
    results.append("Extraction completed successfully.")
    return results


def cleanup_zip_file(zip_path: str) -> list:
    """
    Remove a temporary zip file.
    
    Args:
        zip_path (str): The path to the zip file to remove.
        
    Returns:
        list: A list of status messages.
    """
    results = []
    if os.path.exists(zip_path):
        os.remove(zip_path)
        results.append("Temporary zip file removed.")
    
    return results


# Register local operation tools
@mcp.tool()
def create_env_file_content() -> str:
    """
    Create content for .env file at Kantan CMS integration.
    This text contains the necessary text to create the environment variables for the integration.
    Note: API key will be hidden.
    """
    env_dict = get_env_dict(default_api_key="")
    return "\n".join([f"{key}={value}" for key, value in env_dict.items()])


@mcp.tool()
def download_and_unzip_builder_script(root_path: str, lang: str = "python") -> str:
    """
    Download and unzip the builder script for Kantan CMS.
    This script is used to create a build file for Kantan CMS.
    Args:
        root_path (str): The path to the root directory of your project.
        lang (str): The language of the builder script. Options are "bun" or "python".
    """

    if lang.lower() not in ["python", "bun"]:
        return f"Error: Invalid language '{lang}'. Supported languages are 'python' or 'bun'."
    
    # Set the URL based on the language
    url_paths = {
        "python": "https://github.com/kantan-cms/website-base-py/archive/refs/tags/v0.0.0.zip",
        "bun": "https://github.com/kantan-cms/website-base-bun/archive/refs/tags/v0.0.0.zip"
    }

    url = url_paths[lang.lower()]
    results = []
    
    # Download the zip file
    zip_path, download_results = download_zip_file(url)
    results.extend(download_results)
    
    # Extract the zip file
    extract_results = extract_zip_file(zip_path, root_path)
    results.extend(extract_results)
    
    # Clean up the zip file
    cleanup_results = cleanup_zip_file(zip_path)
    results.extend(cleanup_results)
    
    return "\n".join(results)
