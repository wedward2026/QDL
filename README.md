# QDL MCP Server

An MCP (Model Context Protocol) server that provides Claude with direct access to the [Qatar Digital Library](https://www.qdl.qa/) — a collection of over 2 million digitized pages of historical materials about the Gulf region and Middle East.

## Tools

| Tool | Description |
|------|-------------|
| `search_qdl` | Search the QDL archive by keyword with pagination |
| `get_document_metadata` | Fetch full IIIF metadata for a document |
| `get_document_pages` | List pages/canvases with image URLs |
| `get_page_image_url` | Construct IIIF Image API URLs for page images |
| `get_timeline` | Get temporal distribution of search results |

## Setup

### 1. Install dependencies

```bash
cd /path/to/QDL
pip install -r requirements.txt
```

### 2. Configure Claude Code

Add to your Claude Code MCP settings (`~/.claude/settings.json` or project `.claude/settings.json`):

```json
{
  "mcpServers": {
    "qdl": {
      "command": "python3",
      "args": ["-m", "qdl_mcp_server"],
      "cwd": "/path/to/QDL"
    }
  }
}
```

### 3. Use it

Once configured, Claude can directly search and retrieve QDL documents during conversations. Example queries:

- "Search QDL for documents about the Treaty of Seeb"
- "Find British political agency records related to Muscat"
- "Get the metadata for this QDL document: 81055/vdc_100023575853.0x000001"

## API Reference

The server wraps two QDL APIs:

- **QDL Search** (`/en/search/site/{query}`) — full-text search of the archive
- **IIIF Presentation API 2.0** — structured document metadata and page information
- **IIIF Image API 2.0** — page images (max 1200px width)
- **Timeline endpoint** (`/en/search/timeline/{query}`) — faceted date distribution

No authentication is required. QDL content is freely accessible.
