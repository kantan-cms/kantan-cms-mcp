import os
from kantan_cms_mcp import mcp


def get_env_vars() -> tuple[str, str]:
    """Get the value of an environment variable."""
    project_id = os.environ.get("PROJECT_ID")
    api_key = os.environ.get("CMS_API_KEY")
    return project_id, api_key


def validate_env_vars(project_id: str, api_key: str) -> bool:
    """Validate the environment variables."""
    if not project_id:
        raise ValueError("PROJECT_ID environment variable is not set.")
    if not api_key:
        raise ValueError("CMS_API_KEY environment variable is not set.")
    return True


if __name__ == "__main__":
    try:
        # Validate environment variables
        project_id, api_key = get_env_vars()
        validate_env_vars(project_id, api_key)
        print("Environment variables validated successfully.")
        
        # Run the MCP server
        mcp.run()
    except ValueError as e:
        print(f"Error: {e}")
        print("MCP server startup aborted due to missing environment variables.")
        exit(1)
