# src/open_llms_txt/web/remote_scraper.py

from typing import Dict
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import logging

import httpx

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class WebScraper(BaseScraper):
    def __init__(self, root: str):
        super().__init__(root)
        self.domain = urlparse(self.root).netloc
        self.client = httpx.AsyncClient(follow_redirects=True)

    async def _fetch(self, url: str) -> str:
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.warning(f"⚠️ Could not fetch {url}: {e}")
            return ""

    async def collect_views(self) -> Dict[str, str]:
        html = await self._fetch(self.root)
        if not html:
            return {}

        soup = BeautifulSoup(html, "html.parser")
        links = soup.find_all("a", href=True)

        content_map = {}

        for link in links:
            href = link["href"]
            parsed_href = urlparse(href)

            if parsed_href.netloc == "" or parsed_href.netloc == self.domain:
                full_url = urljoin(self.root, href)
                logger.debug(f"Current subview detected: {full_url}")
                self.subpages.add(full_url)

        for url in self.subpages:
            content = await self._fetch(url)
            if content:
                content_map[url] = content

        return content_map

    async def close(self):
        await self.client.aclose()
