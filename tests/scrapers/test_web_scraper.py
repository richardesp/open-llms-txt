# Copyright (c) 2025 Ricardo Espantaleón Pérez
# SPDX-License-Identifier: Apache-2.0

from typing import Dict, Optional

import pytest

from open_llms_txt.scrapers.web_scraper import WebScraper


class DummyResponse:
    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class DummyAsyncClient:
    """
    Minimal stand-in for httpx.AsyncClient used in tests.
    Provide a mapping of url -> (text, status_code) to control responses.
    """

    def __init__(self, routes: Optional[Dict[str, DummyResponse]] = None):
        self._routes = routes or {}
        self._closed = False

    async def get(self, url: str):
        if url not in self._routes:
            raise RuntimeError(f"Unknown URL {url}")
        resp = self._routes[url]
        if isinstance(resp, str):
            resp = DummyResponse(resp, 200)
        resp.raise_for_status()
        return resp

    async def aclose(self):
        self._closed = True

    @property
    def is_closed(self) -> bool:
        return self._closed


@pytest.mark.asyncio
async def test_fetch_content_success():
    root = "https://example.com/"
    scraper = WebScraper(root)

    html_ok = "<html><body><h1>OK</h1></body></html>"
    scraper.client = DummyAsyncClient(routes={f"{root}page": html_ok})

    out = await scraper.fetch_content(f"{root}page")
    assert "<h1>OK</h1>" in out

    await scraper.close()


@pytest.mark.asyncio
async def test_fetch_content_failure_logs_and_returns_empty(caplog):
    root = "https://example.com/"
    scraper = WebScraper(root)

    scraper.client = DummyAsyncClient(routes={})

    with caplog.at_level("WARNING"):
        out = await scraper.fetch_content(f"{root}missing")
    assert out == ""
    assert any("Could not fetch" in rec.getMessage() for rec in caplog.records)

    await scraper.close()


@pytest.mark.asyncio
async def test_collect_root_subpages_same_domain_only():
    """
    Root page links to:
      - /about                        -> included (relative, same domain)
      - https://example.com/contact   -> included (absolute, same domain)
      - https://other.com/x           -> NOT included (external domain)
      - #top / ["not-a-string"]       -> ignored for expectations
    """
    root = "https://example.com/"
    scraper = WebScraper(root)

    root_html = """
    <html><body>
      <h1>Home</h1>
      <a href="/about">About</a>
      <a href="https://example.com/contact">Contact</a>
      <a href="https://other.com/x">External</a>
      <a href="#top">Anchor</a>
      <a href='["not-a-string"]'>Weird</a>
    </body></html>
    """

    about_html = "<html><body><h1>About Title</h1></body></html>"
    contact_html = "<html><body><p>No H1 here</p></body></html>"

    from urllib.parse import urljoin

    about_url = urljoin(root, "/about")  # https://example.com/about
    contact_url = urljoin(
        root, "https://example.com/contact"
    )  # https://example.com/contact
    external_url = "https://other.com/x"  # excluded

    routes = {
        root: root_html,
        root.rstrip(
            "/"
        ): root_html,  # handle both https://example.com and https://example.com/
        about_url: about_html,
        contact_url: contact_html,
        # external_url intentionally omitted (shouldn't be requested at all)
    }

    scraper.client = DummyAsyncClient(routes=routes)

    content_map = await scraper.collect_root_subpages()

    # Only same-domain pages included
    assert set(content_map.keys()) == {about_url, contact_url}
    assert content_map[about_url] == "About Title"
    assert content_map[contact_url] == "Untitled"

    # Ensure external wasn't even added to discovered subpages
    assert external_url not in scraper.root_subpages

    await scraper.close()


@pytest.mark.asyncio
async def test_collect_root_subpages_empty_root_returns_empty_map():
    root = "https://example.com/"
    scraper = WebScraper(root)

    scraper.client = DummyAsyncClient(routes={root: ""})  # empty HTML
    out = await scraper.collect_root_subpages()
    assert out == {}

    await scraper.close()


@pytest.mark.asyncio
async def test_close_closes_httpx_client():
    root = "https://example.com/"
    scraper = WebScraper(root)
    scraper.client = DummyAsyncClient(routes={})
    assert scraper.client.is_closed is False

    await scraper.close()
    assert scraper.client.is_closed is True
