# Kantan CMS MCP Tools

This repository contains MCP (Model Context Protocol) tools for interacting with the Kantan CMS API.

## Setup

1. Clone this repository
   ```
   git clone https://github.com/kantan-cms/kantan-cms-mcp.git
   ```
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

## MCP Setup

```json
{
  "mcpServers": {
    "kantan-cms-instruction": {
      "command": "python",
      "args": ["<absolute path to kantan-cms-mcp>/main.py"],
      "disabled": false,
      "env": {
        "PROJECT_ID": "<Project ID>",
        "CMS_API_KEY": "<API Key>"
      }
    }
  },
  ...
}
```


## Environment Variables

- `PROJECT_ID`: Your Kantan CMS project ID.
- `CMS_API_KEY`: Your Kantan CMS API key.

These environment variables are required for authentication with the Kantan CMS API.
