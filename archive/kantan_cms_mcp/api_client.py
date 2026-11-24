import requests
import os
from typing import Optional


class KantanCMSApiClient:
    """
    Client for interacting with the Kantan CMS API.
    """
    
    def __init__(self, base_url: str = "https://api.kantan-cms.com/"):
        """
        Initialize the API client.
        
        Args:
            base_url (str): The base URL for the API.
        """
        self.base_url = os.path.join(base_url, "v1", "api")
        self.project_id = os.environ.get("PROJECT_ID")
        self.api_key = os.environ.get("CMS_API_KEY")
        
        if not self.project_id:
            raise ValueError("PROJECT_ID environment variable is not set.")
        if not self.api_key:
            raise ValueError("CMS_API_KEY environment variable is not set.")
    
    def _create_headers(self) -> dict[str, str]:
        """
        Create the headers for API requests.
        
        Returns:
            dict[str, str]: The headers for the API request.
        """
        return {
            "X-Project-Id": self.project_id,
            "X-API-Key": self.api_key,
        }
    
    def _make_request(self, method: str, endpoint: str, params: Optional[dict[str, any]] = None, data: Optional[dict[str, any]] = None) -> dict[str, any]:
        """
        Make a request to the API.
        
        Args:
            method (str): The HTTP method to use.
            endpoint (str): The API endpoint to request.
            params (Optional[dict[str, any]]): The query parameters for the request.
            data (Optional[dict[str, any]]): The data to send in the request body.
            
        Returns:
            dict[str, any]: The response from the API.
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._create_headers()
        
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=data
        )
        
        response.raise_for_status()
        return response.json()
    
    # Collections API
    
    def list_collections(self, page_size: int = 10, page_num: int = 1, resp: Optional[str] = None) -> dict[str, any]:
        """
        List collections in the project.
        
        Args:
            page_size (int): The number of collections to return per page.
            page_num (int): The page number to return.
            resp (Optional[str]): Additional response formatting options.
            
        Returns:
            dict[str, any]: The collections response.
        """
        params = {
            "page_size": page_size,
            "page_num": page_num
        }
        
        if resp:
            params["resp"] = resp
        
        return self._make_request("GET", "/collections/", params=params)
    
    def count_collections(self) -> dict[str, int]:
        """
        Count collections in the project.
        
        Returns:
            dict[str, int]: The collection count.
        """
        return self._make_request("GET", "/collections_count/")
    
    def get_collection(self, collection_id: str) -> dict[str, any]:
        """
        Get a collection by ID.
        
        Args:
            collection_id (str): The ID of the collection to retrieve.
            
        Returns:
            dict[str, any]: The collection response.
        """
        return self._make_request("GET", f"/collections/{collection_id}")
    
    # Records API
    
    def list_records(self, collection_id: str, page_size: int = 10, page_num: int = 1) -> dict[str, any]:
        """
        List records in a collection.
        
        Args:
            collection_id (str): The ID of the collection to retrieve records from.
            page_size (int): The number of records to return per page.
            page_num (int): The page number to return.
            
        Returns:
            dict[str, any]: The records response.
        """
        params = {
            "page_size": page_size,
            "page_num": page_num
        }
        
        return self._make_request("GET", f"/collections/{collection_id}/records/", params=params)
    
    def get_record(self, collection_id: str, record_id: str) -> dict[str, any]:
        """
        Get a record by ID.
        
        Args:
            collection_id (str): The ID of the collection the record belongs to.
            record_id (str): The ID of the record to retrieve.
            
        Returns:
            dict[str, any]: The record response.
        """
        return self._make_request("GET", f"/collections/{collection_id}/records/{record_id}")
    
    def count_records(self, collection_id: str) -> dict[str, int]:
        """
        Count records in a collection.
        
        Args:
            collection_id (str): The ID of the collection to count records for.
            
        Returns:
            dict[str, int]: The record count.
        """
        return self._make_request("GET", f"/collections/{collection_id}/records_count/")
    
    # API Keys API
    
    def validate_api_key(self) -> dict[str, int]:
        """
        Validate the current API key.
        
        Returns:
            dict[str, int]: The validation response.
        """
        return self._make_request("GET", "/api_key/validate")
    
    # Schemas API
    
    def get_schema_type(self, collection_id: str) -> dict[str, any]:
        """
        Get the schema structure for a collection. Keys are custom_key and values are the types.
        
        Args:
            collection_id (str): The ID of the collection to get the schema for.
            
        Returns:
            dict[str, any]: The schema type response.
        """
        return self._make_request("GET", f"/collections/{collection_id}/schema_type")
