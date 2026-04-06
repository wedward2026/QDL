"""Parsers for QDL HTML search results and IIIF manifest JSON."""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup, Tag


# ---------------------------------------------------------------------------
# Search result parsing
# ---------------------------------------------------------------------------

def parse_search_results(html: str) -> dict[str, Any]:
    """Parse QDL search results HTML into structured data.

    Returns a dict with keys:
        total: estimated total results (int or None)
        results: list of result dicts
        current_page: current page number (0-indexed)
        has_next_page: whether there are more pages
    """
    soup = BeautifulSoup(html, "lxml")

    # Total results count — usually in a heading or info line
    total = _extract_total(soup)

    results: list[dict[str, Any]] = []

    # QDL uses Drupal search; results are typically in <li> inside
    # <ol class="search-results"> or <div class="search-result">
    # We try multiple selectors to be resilient.
    result_items = (
        soup.select("ol.search-results li")
        or soup.select("li.search-result")
        or soup.select("div.view-content div.views-row")
        or soup.select(".search-result")
    )

    for item in result_items:
        result = _parse_single_result(item)
        if result:
            results.append(result)

    # Pagination
    current_page = 0
    has_next = False
    pager = soup.select_one("ul.pager, nav.pager, .item-list ul.pager")
    if pager:
        current_li = pager.select_one("li.pager-current, li.is-active")
        if current_li:
            try:
                current_page = int(current_li.get_text(strip=True)) - 1
            except ValueError:
                pass
        next_link = pager.select_one("li.pager-next a, li.pager__item--next a")
        has_next = next_link is not None

    return {
        "total": total,
        "results": results,
        "current_page": current_page,
        "has_next_page": has_next,
    }


def _extract_total(soup: BeautifulSoup) -> int | None:
    """Try to extract total result count from the page."""
    # Look for patterns like "Showing 1 - 10 of 1234 results" or "1234 results"
    for tag in soup.find_all(["h2", "h3", "div", "p", "span"]):
        text = tag.get_text(" ", strip=True)
        m = re.search(r"([\d,]+)\s+results?", text, re.IGNORECASE)
        if m:
            return int(m.group(1).replace(",", ""))
    return None


def _parse_single_result(item: Tag) -> dict[str, Any] | None:
    """Parse a single search result element."""
    # Title + link
    title_tag = item.select_one("h3 a, h2 a, .title a, a.search-result__title")
    if not title_tag:
        # fallback: first <a> with text
        title_tag = item.find("a", string=True)
    if not title_tag:
        return None

    title = title_tag.get_text(strip=True)
    href = title_tag.get("href", "")
    url = href if href.startswith("http") else f"https://www.qdl.qa{href}"

    # Extract VDC identifier from URL
    vdc_id = _extract_vdc_id(url)

    # Description / snippet
    snippet_tag = item.select_one(
        ".search-snippet, .search-result__snippet, .field-content, p"
    )
    snippet = snippet_tag.get_text(" ", strip=True) if snippet_tag else ""

    # Date
    date_tag = item.select_one(".date, .search-result__date, time")
    date = ""
    if date_tag:
        date = date_tag.get("datetime", "") or date_tag.get_text(strip=True)

    # Type / content-type label
    type_tag = item.select_one(".search-result__type, .content-type, .type")
    content_type = type_tag.get_text(strip=True) if type_tag else ""

    return {
        "title": title,
        "url": url,
        "vdc_id": vdc_id,
        "snippet": snippet,
        "date": date,
        "content_type": content_type,
    }


def _extract_vdc_id(url: str) -> str:
    """Extract the VDC record path from a QDL archive URL.

    Example URL: https://www.qdl.qa/en/archive/81055/vdc_100023575853.0x000001
    Returns: '81055/vdc_100023575853.0x000001'
    """
    m = re.search(r"/archive/([\d]+/vdc_[\w.]+)", url)
    return m.group(1) if m else ""


# ---------------------------------------------------------------------------
# IIIF Manifest parsing
# ---------------------------------------------------------------------------

def parse_manifest(data: dict[str, Any]) -> dict[str, Any]:
    """Parse an IIIF Presentation API 2.0 manifest into structured metadata."""
    label = _get_label(data.get("label", ""))
    description = _get_label(data.get("description", ""))
    metadata = _parse_metadata_pairs(data.get("metadata", []))

    sequences = data.get("sequences", [])
    canvases = []
    if sequences:
        canvases = sequences[0].get("canvases", [])

    structures = data.get("structures", [])
    toc = [
        {
            "label": _get_label(s.get("label", "")),
            "canvases": s.get("canvases", []),
        }
        for s in structures
    ]

    pages = []
    for i, canvas in enumerate(canvases):
        page_info: dict[str, Any] = {
            "index": i,
            "label": _get_label(canvas.get("label", f"Page {i + 1}")),
            "width": canvas.get("width"),
            "height": canvas.get("height"),
        }
        # Extract image URL from canvas
        images = canvas.get("images", [])
        if images:
            resource = images[0].get("resource", {})
            service = resource.get("service", {})
            page_info["image_url"] = resource.get("@id", "")
            page_info["image_service"] = service.get("@id", "")
        pages.append(page_info)

    return {
        "label": label,
        "description": description,
        "metadata": metadata,
        "page_count": len(canvases),
        "pages": pages,
        "table_of_contents": toc,
        "attribution": data.get("attribution", ""),
        "manifest_url": data.get("@id", ""),
    }


def parse_pages(
    data: dict[str, Any],
    start: int = 0,
    count: int | None = None,
) -> list[dict[str, Any]]:
    """Extract page info from a manifest, optionally slicing."""
    parsed = parse_manifest(data)
    pages = parsed["pages"]
    end = start + count if count is not None else len(pages)
    return pages[start:end]


def _get_label(value: Any) -> str:
    """Normalise a IIIF label which may be a string, list, or dict."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(item.get("@value", str(item)))
        return " ".join(parts)
    if isinstance(value, dict):
        return value.get("@value", str(value))
    return str(value) if value else ""


def _parse_metadata_pairs(
    metadata: list[dict[str, Any]],
) -> dict[str, str]:
    """Parse IIIF metadata array of {label, value} pairs."""
    result: dict[str, str] = {}
    for entry in metadata:
        key = _get_label(entry.get("label", ""))
        val = _get_label(entry.get("value", ""))
        if key:
            result[key] = val
    return result
