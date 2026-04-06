"""HTTP client for the Qatar Digital Library (QDL) API."""

import httpx

BASE_URL = "https://www.qdl.qa"
IIIF_IMAGE_BASE = "https://iiif.qdl.qa/iiif/images"
DEFAULT_TIMEOUT = 30.0

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


class QDLClient:
    """Client for interacting with QDL's web and IIIF APIs."""

    def __init__(self):
        self._client = httpx.Client(
            headers=HEADERS,
            follow_redirects=True,
            timeout=DEFAULT_TIMEOUT,
        )

    def close(self):
        self._client.close()

    def search(self, query: str, page: int = 0) -> httpx.Response:
        """Search QDL archive. Returns raw HTML response."""
        params = {}
        if page > 0:
            params["page"] = str(page)
        url = f"{BASE_URL}/en/search/site/{query}"
        return self._client.get(url, params=params)

    def search_timeline(self, query: str) -> httpx.Response:
        """Fetch timeline/facet data for a search query. Returns JSON."""
        url = f"{BASE_URL}/en/search/timeline/{query}"
        return self._client.get(
            url,
            headers={**HEADERS, "Accept": "application/json, */*;q=0.1"},
        )

    def get_manifest(self, record_id: str) -> httpx.Response:
        """Fetch IIIF manifest for a document.

        record_id: the VDC path segment, e.g.
            '81055/vdc_100023575853.0x000001' or just the archive path
            after /en/archive/.
        """
        url = f"{BASE_URL}/en/iiif/{record_id}/manifest"
        return self._client.get(
            url,
            headers={**HEADERS, "Accept": "application/ld+json, application/json"},
        )

    def get_archive_page(self, record_id: str) -> httpx.Response:
        """Fetch an archive detail page. Returns raw HTML."""
        url = f"{BASE_URL}/en/archive/{record_id}"
        return self._client.get(url)

    @staticmethod
    def build_image_url(
        image_id: str,
        width: int = 1200,
        region: str = "full",
        rotation: int = 0,
        quality: str = "default",
        fmt: str = "jpg",
    ) -> str:
        """Construct a IIIF Image API URL.

        image_id: the image identifier on the IIIF server
        width: max pixel width (QDL caps at 1200)
        """
        capped_width = min(width, 1200)
        size = f"{capped_width},"
        return (
            f"{IIIF_IMAGE_BASE}/{image_id}"
            f"/{region}/{size}/{rotation}/{quality}.{fmt}"
        )
