"""MCP server for the Qatar Digital Library (QDL).

Provides tools to search QDL's archive, fetch IIIF document metadata,
list pages, get image URLs, and retrieve timeline/facet data.
"""

from __future__ import annotations

import json
import traceback

from mcp.server.fastmcp import FastMCP

from .qdl_client import QDLClient
from .parsers import parse_manifest, parse_pages, parse_search_results

mcp = FastMCP(
    "Qatar Digital Library",
    instructions=(
        "Search and retrieve documents from the Qatar Digital Library (QDL), "
        "a collection of over 2 million digitized pages of historical materials "
        "about the Gulf region and Middle East."
    ),
)

client = QDLClient()


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def search_qdl(query: str, page: int = 0) -> str:
    """Search the Qatar Digital Library archive by keyword.

    Args:
        query: Search terms (e.g. 'Treaty of Seeb', 'Oman oil concession').
        page: Results page number (0-indexed). Each page has ~10 results.

    Returns:
        JSON with total count, list of results (title, url, vdc_id, snippet,
        date, content_type), current_page, and has_next_page.
    """
    try:
        resp = client.search(query, page=page)
        resp.raise_for_status()
        parsed = parse_search_results(resp.text)
        return json.dumps(parsed, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e), "traceback": traceback.format_exc()})


@mcp.tool()
def get_document_metadata(record_id: str) -> str:
    """Fetch full metadata for a QDL document via its IIIF manifest.

    Args:
        record_id: The archive path, e.g. '81055/vdc_100023575853.0x000001'.
                   This is the vdc_id returned by search_qdl.

    Returns:
        JSON with label, description, metadata fields, page_count,
        table_of_contents, and attribution.
    """
    try:
        resp = client.get_manifest(record_id)
        resp.raise_for_status()
        data = resp.json()
        parsed = parse_manifest(data)
        # Don't include full pages list in metadata (use get_document_pages)
        parsed.pop("pages", None)
        return json.dumps(parsed, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e), "traceback": traceback.format_exc()})


@mcp.tool()
def get_document_pages(
    record_id: str,
    start: int = 0,
    count: int = 20,
) -> str:
    """List pages (canvases) from a QDL document.

    Args:
        record_id: The archive path, e.g. '81055/vdc_100023575853.0x000001'.
        start: Index of first page to return (0-indexed).
        count: Number of pages to return (default 20, max 100).

    Returns:
        JSON list of pages with index, label, width, height,
        image_url, and image_service.
    """
    try:
        count = min(count, 100)
        resp = client.get_manifest(record_id)
        resp.raise_for_status()
        data = resp.json()
        pages = parse_pages(data, start=start, count=count)
        return json.dumps(pages, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e), "traceback": traceback.format_exc()})


@mcp.tool()
def get_page_image_url(
    image_id: str,
    width: int = 1200,
) -> str:
    """Construct a IIIF Image API URL for a specific page.

    Use the image_service value from get_document_pages to derive the
    image_id, or pass the full IIIF image service URL directly.

    Args:
        image_id: IIIF image identifier or full image service URL.
                  If a full URL is given, the path portion after /images/ is used.
        width: Desired image width in pixels (max 1200 per QDL limits).

    Returns:
        The full IIIF Image API URL for the page image.
    """
    # If user passed a full service URL, extract the image id
    if image_id.startswith("http"):
        parts = image_id.split("/images/", 1)
        if len(parts) == 2:
            image_id = parts[1].rstrip("/")

    url = QDLClient.build_image_url(image_id, width=width)
    return json.dumps({"image_url": url})


@mcp.tool()
def get_timeline(query: str) -> str:
    """Get temporal distribution of search results from QDL.

    Useful for understanding when documents matching a query were created.

    Args:
        query: Search terms (same as search_qdl).

    Returns:
        JSON with timeline/facet data showing document counts by date range.
    """
    try:
        resp = client.search_timeline(query)
        resp.raise_for_status()
        data = resp.json()
        return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e), "traceback": traceback.format_exc()})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    mcp.run()


if __name__ == "__main__":
    main()
