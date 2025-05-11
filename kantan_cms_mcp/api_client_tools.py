from .server import mcp, BASE_URL
from .api_client import KantanCMSApiClient


# Register API client tools
@mcp.tool()
def list_collections(page_size: int = 10, page_num: int = 1, resp: str = None) -> dict:
    """
    List collections in the project. This is useful for retrieving metadata about the collections.
    
    Args:
        page_size (int): The number of collections to return per page.
        page_num (int): The page number to return.
        resp (str, optional): Additional response formatting options.
    
    Returns:
        dict: A dictionary containing the collections.
    """
    client = KantanCMSApiClient(BASE_URL)
    return client.list_collections(page_size, page_num, resp)


@mcp.tool()
def count_collections() -> dict:
    """
    Count collections in the project. This is useful for pagination and understanding the size of the dataset.
    
    Returns:
        dict: A dictionary containing the count of collections.
    """
    client = KantanCMSApiClient(BASE_URL)
    return client.count_collections()


@mcp.tool()
def get_collection(collection_id: str) -> dict:
    """
    Get a collection by ID. This will get the collection details for a specific collection.
    
    Args:
        collection_id (str): The ID of the collection to retrieve.
    
    Returns:
        dict: A dictionary containing the collection details.
    """
    client = KantanCMSApiClient(BASE_URL)
    return client.get_collection(collection_id)


@mcp.tool()
def list_records(collection_id: str, page_size: int = 10, page_num: int = 1) -> dict:
    """
    List records in a collection. This is useful for retrieving data from a specific collection.
    
    Args:
        collection_id (str): The ID of the collection to retrieve records from.
        page_size (int): The number of records to return per page.
        page_num (int): The page number to return.
    
    Returns:
        dict: A dictionary containing the records.
    """
    client = KantanCMSApiClient(BASE_URL)
    return client.list_records(collection_id, page_size, page_num)


@mcp.tool()
def get_record(collection_id: str, record_id: str) -> dict:
    """
    Get a record by ID. This will get the record details for a specific record in a collection.
    
    Args:
        collection_id (str): The ID of the collection the record belongs to.
        record_id (str): The ID of the record to retrieve.
    
    Returns:
        dict: A dictionary containing the record details.
    """
    client = KantanCMSApiClient(BASE_URL)
    return client.get_record(collection_id, record_id)


@mcp.tool()
def count_records(collection_id: str) -> dict:
    """
    Count records in a collection. This is useful for pagination and understanding the size of the dataset.
    
    Args:
        collection_id (str): The ID of the collection to count records for.
    
    Returns:
        dict: A dictionary containing the count of records.
    """
    client = KantanCMSApiClient(BASE_URL)
    return client.count_records(collection_id)


@mcp.tool()
def validate_api_key() -> dict:
    """
    Validate the current API key.
    This allows you to check if the API key is valid and has the necessary permissions.
    
    Returns:
        dict: A dictionary containing the validation status.
    """
    client = KantanCMSApiClient(BASE_URL)
    return client.validate_api_key()


@mcp.tool()
def get_schema_type(collection_id: str) -> dict:
    """
    Get the schema type structure for a collection.
    For getting records, they can helpful to understand the data structure to map the data in they way you want.
    For form integratoin, they can be helpful to post the data in the right format.
    Keys are custom_key and values are the types.
    
    Args:
        collection_id (str): The ID of the collection to get the schema for.
    
    Returns:
        dict: A dictionary containing the schema type structure.
    """
    client = KantanCMSApiClient(BASE_URL)
    return client.get_schema_type(collection_id)
