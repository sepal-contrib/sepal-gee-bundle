"""Pure helpers to extract JavaScript source from an Earth Engine Apps URL.

The legacy implementation was ported from:
https://github.com/samapriya/gee_asset_manager_addon/blob/master/geeadd/app2script.py

An Earth Engine App page embeds one or more ``<script>`` tags whose body
starts with ``init("https://...")``. That URL returns a JSON blob with a
``path`` field and a ``dependencies`` mapping; the source we care about
lives at ``dependencies[path]``.
"""

from __future__ import annotations

import re
from typing import List

import requests
from bs4 import BeautifulSoup

from apps.gee_source.params import EE_APP_URL_PREFIXES, HTTP_TIMEOUT, USER_AGENT

_INIT_CALL_RE = re.compile(r'\binit\(\s*"([^"]+)"')


def _headers() -> dict:
    return {"User-Agent": USER_AGENT}


def fetch_app_html(app_url: str) -> str:
    """Fetch the HTML body of an Earth Engine App URL.

    Args:
        app_url: The public ``https://...earthengine.app/view/...`` URL.

    Returns:
        The response body as a string.

    Raises:
        ValueError: If the URL does not start with an allowed prefix.
        requests.RequestException: On network failure or a non-2xx status.
    """
    if not app_url or not app_url.startswith(EE_APP_URL_PREFIXES):
        raise ValueError(f"Invalid Earth Engine App URL: {app_url!r}")

    response = requests.get(app_url, headers=_headers(), timeout=HTTP_TIMEOUT)
    response.raise_for_status()
    return response.text


def parse_init_urls(html: str) -> List[str]:
    """Return every ``init(...)`` URL embedded in an Earth Engine App page.

    Only URLs that start with ``https://`` are kept — the rest are local
    initialisation calls that never carry the source.
    """
    soup = BeautifulSoup(html, "html.parser")
    urls: List[str] = []
    seen: set[str] = set()
    for script in soup.find_all("script"):
        body = script.string
        if body is None:
            continue
        for match in _INIT_CALL_RE.finditer(body):
            url = match.group(1).replace("\\/", "/")
            if url.startswith("https://") and url not in seen:
                seen.add(url)
                urls.append(url)
    return urls


def _extract_dependency_source(payload: dict) -> str:
    """Pull ``dependencies[path]`` out of the init payload."""
    path = payload.get("path")
    deps = payload.get("dependencies") or {}
    if path and path in deps:
        return str(deps[path]).strip()
    return ""


def extract_js_source(app_url: str, *, fetcher=None) -> str:
    """Extract the JavaScript source of the given Earth Engine App.

    Args:
        app_url: Public Earth Engine App URL.
        fetcher: Optional callable ``(url) -> requests.Response`` used to
            retrieve init payloads. Exposed for testing; defaults to
            ``requests.get`` with the module user agent.

    Returns:
        The concatenated JavaScript source (empty string if none was found).

    Raises:
        ValueError: If the URL is invalid.
        requests.RequestException: On network failures fetching HTML / JSON.
    """
    if fetcher is None:

        def fetcher(url: str):
            return requests.get(url, headers=_headers(), timeout=HTTP_TIMEOUT)

    html = fetch_app_html(app_url)
    init_urls = parse_init_urls(html)

    chunks: List[str] = []
    for url in init_urls:
        response = fetcher(url)
        response.raise_for_status()
        payload = response.json()
        source = _extract_dependency_source(payload)
        if source:
            chunks.append(source)

    return "\n".join(chunks)
