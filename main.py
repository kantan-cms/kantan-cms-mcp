from fastmcp import FastMCP
import requests
import os

VERSION = "0.1.0"
mcp = FastMCP("Kantan CMS Tools 🚀")
BASE_URL = "https://api-dev.kantan-cms.com"


def get_env_vars() -> tuple[str, str]:
    """Get the value of an environment variable."""
    project_id = os.environ.get("PROJECT_ID")
    api_key = os.environ.get("CMS_API_KEY")
    return project_id, api_key


def get_env_dict(defult_project_id: str | None = None, default_api_key: str | None = None) -> dict:
    project_id, api_key = get_env_vars()
    env_dict = {
        "PROJECT_ID": defult_project_id or project_id,
        "CMS_API_KEY": default_api_key or api_key,
    }
    return env_dict


def validate_env_vars(project_id: str, api_key: str) -> bool:
    """Validate the environment variables."""
    if not project_id:
        raise ValueError("PROJECT_ID environment variable is not set.")
    if not api_key:
        raise ValueError("CMS_API_KEY environment variable is not set.")
    return True


def create_api_header(project_id: str, api_key: str) -> dict:
    """Create the headers for the API request."""
    return {
        "X-Project-ID": project_id,
        "X-API-Key": api_key,
    }


def fetch_via_api(path: str) -> requests.Response:
    url = f"{BASE_URL}/v1/docs/{path}"
    
    project_id, api_key = get_env_vars()
    validate_env_vars(project_id, api_key)
    headers = create_api_header(project_id, api_key)
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # Raise an exception for HTTP errors
    return response


def get_notification() -> str:
    """Fetch the latest notification from Kantan CMS"""
    try:
        response = fetch_via_api(f"updates?version={VERSION}")
    except Exception as e:
        print("Error fetching notification", str(e))
        return ""
    return f"Note: {response.text}"


def fetch_text(path: str) -> str:
    """Fetch text file from the Kantan CMS documentation"""
    notification = get_notification()
    response = fetch_via_api(path)
    return "\n".join([t for t in [notification, response.text] if t]) 


@mcp.tool()
def get_category_api(category_name: str) -> dict:
    """
    Get api information on how to implement a specific feature in Kantan CMS.
    URL: https://api-dev.kantan-cms.com/v1/doc/api/{path}
    
    Args:
        category_name (str): The path to the specific feature instructions.
    """
    
    return fetch_text(f"api/{category_name}")


@mcp.tool()
def get_toc() -> dict:
    """
    Get the table of contents for Kantan CMS API documentation.
    This allows you to see the available features and their paths.
    URL: https://api-dev.kantan-cms.com/v1/doc/api/

    """
    return fetch_text("api/")


@mcp.tool()
def get_instruction_for_builing() -> dict:
    """
    Get the markdown instructions for creating a build file for Kantan CMS.
    This is the first document you would read in order to integrate with Kantan CMS.
    
    """
    return fetch_text("instruction/build")


@mcp.tool()
def get_instruction_for_form_integartion() -> dict:
    """
    Get the markdown instructions for integrating forms with Kantan CMS.
    If you have a form 
    """
    return fetch_text("instruction/form")


@mcp.tool()
def create_env_file_content() -> str:
    """
    Create content for .env file at Kantan CMS integration.
    This text contains the necessary text to create the environment variables for the integration.
    Note: API key will be hidden.
    """
    env_dict = get_env_dict(default_api_key="")
    return "\n".join([f"{key}={value}" for key, value in env_dict.items()])


if __name__ == "__main__":
    try:
        project_id, api_key = get_env_vars()
        validate_env_vars(project_id, api_key)
        print("Environment variables validated successfully.")
        mcp.run()
    except ValueError as e:
        print(f"Error: {e}")
        print("MCP server startup aborted due to missing environment variables.")
        exit(1)
