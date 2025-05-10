# Kantan CMS MCP Server

This MCP server provides tools to fetch documentation and implementation instructions for Kantan CMS, a simple and easy-to-use content management system.

## What is this MCP Server?

The Kantan CMS MCP server is a Model Context Protocol (MCP) server that connects to the Kantan CMS API to fetch documentation and implementation instructions. It allows AI assistants to access up-to-date information about Kantan CMS features and how to implement them.

## Dependencies

This MCP server requires the following dependencies:

```bash
fastmcp==2.3.0
requests==2.31.0
```

You can install these dependencies using pip:

```bash
pip install -r requirements.txt
```

## Configuration

### Environment Variables

The Kantan CMS MCP server uses the following environment variables:

- `PROJECT_ID`: Your Kantan CMS project ID, which will be sent as the `X-Project-Id` header in API requests
- `CMS_API_KEY`: Your Kantan CMS API key, which will be sent as the `X-API-Key` header in API requests

### MCP Configuration

To make this MCP server available to your AI assistant, add it to your `.mcp.json` file in your home directory:

```json
{
  "servers": [
    {
      "name": "kantan-cms-tools",
      "command": ["python", "/path/to/kantan-cms-mcp/main.py"],
      "auto_start": true,
      "env": {
        "PROJECT_ID": "your-project-id",
        "CMS_API_KEY": "your-api-key"
      }
    }
  ]
}
```

Configuration options:

- `name`: A unique identifier for the server (e.g., "kantan-cms-tools")
- `command`: The command to start the server (adjust the path to where you've cloned this repository)
- `auto_start`: Whether to automatically start the server when your AI assistant is launched
- `env`: Environment variables for the server process (your Kantan CMS credentials)

## Running the Server

To run the server manually:

```bash
python main.py
```

By default, the server will run on port 8080.

## Using the MCP Server

Once the server is configured and running, you can use its tools with your AI assistant:

```
<use_mcp_tool>
<server_name>kantan-cms-tools</server_name>
<tool_name>get_instructions</tool_name>
<arguments>
{
  "category_name": "collections"
}
</arguments>
</use_mcp_tool>
```

To get the table of contents:

```
<use_mcp_tool>
<server_name>kantan-cms-tools</server_name>
<tool_name>get_toc</tool_name>
<arguments>
{}
</arguments>
</use_mcp_tool>
```

## API Endpoints

The Kantan CMS API provides endpoints for managing:

- Collections: Content types and their schemas
- Records: Content entries within collections
- Forms: User-facing forms and their submissions
- API Keys: Authentication tokens for API access
- Hosting: Deployment and hosting settings

For detailed API documentation, use the `get_toc` tool to see all available endpoints and the `get_instructions` tool to get specific implementation details.
