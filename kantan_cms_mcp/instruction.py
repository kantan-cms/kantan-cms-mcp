from .server import mcp
from .api_doc import fetch_text


# Register instruction tools
@mcp.tool()
def get_instruction_for_building() -> dict:
    """
    Get the markdown instructions for creating a build file for Kantan CMS.
    This is the first document you would read in order to create a building script which, get records, builds the website, and push the built website to Kantan CMS.
    """
    return fetch_text("instruction/build")


@mcp.tool()
def get_instruction_for_form_integartion() -> dict:
    """
    Get the markdown instructions for integrating forms with Kantan CMS.
    If you have a form on your website, you can get instruction on how to send the form data to Kantan CMS.
    """
    return fetch_text("instruction/form")
