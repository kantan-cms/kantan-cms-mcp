# Kantan CMS MCP Tools

This repository contains MCP (Model Context Protocol) tools for interacting with the Kantan CMS API.

## Setup

1. Clone this repository
2. Install the dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set the required environment variables:
   ```
   export PROJECT_ID=your_project_id
   export CMS_API_KEY=your_api_key
   ```
4. Run the MCP server:
   ```
   python main.py
   ```

## Available Tools

### Documentation Tools

- `get_category_api(category_name)`: Get API information on how to implement a specific feature in Kantan CMS.
- `get_toc()`: Get the table of contents for Kantan CMS API documentation.
- `get_instruction_for_building()`: Get the markdown instructions for creating a build file for Kantan CMS.
- `get_instruction_for_form_integartion()`: Get the markdown instructions for integrating forms with Kantan CMS.
- `create_env_file_content()`: Create content for .env file at Kantan CMS integration.
- `download_and_unzip_builder_script(root_path, lang)`: Download and unzip the builder script for Kantan CMS.

### API Client Tools

#### Collections API

- `list_collections(page_size, page_num, resp)`: List collections in the project.
- `count_collections()`: Count collections in the project.
- `get_collection(collection_id)`: Get a collection by ID.

#### Records API

- `list_records(collection_id, page_size, page_num)`: List records in a collection.
- `get_record(collection_id, record_id)`: Get a record by ID.
- `count_records(collection_id)`: Count records in a collection.

#### API Keys API

- `validate_api_key()`: Validate the current API key.

#### Schemas API

- `get_schema_type(collection_id)`: Get the schema type structure for a collection.

## Example Usage

```python
# List all collections
collections = list_collections()
print(collections)

# Get a specific collection
collection = get_collection("collection_id")
print(collection)

# List records in a collection
records = list_records("collection_id")
print(records)

# Get a specific record
record = get_record("collection_id", "record_id")
print(record)

# Validate API key
validation = validate_api_key()
print(validation)

# Get schema type for a collection
schema = get_schema_type("collection_id")
print(schema)
```

## API Client

The API client is implemented in `api_client.py` and provides a Python interface to the Kantan CMS API. It handles authentication, request formatting, and response parsing.

### KantanCMSApiClient

```python
from api_client import KantanCMSApiClient

# Create a client
client = KantanCMSApiClient()

# List collections
collections = client.list_collections()
print(collections)

# Get a collection
collection = client.get_collection("collection_id")
print(collection)
```

## Environment Variables

- `PROJECT_ID`: Your Kantan CMS project ID.
- `CMS_API_KEY`: Your Kantan CMS API key.

These environment variables are required for authentication with the Kantan CMS API.
