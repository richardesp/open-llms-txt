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
        self.domain = urlparse(self.root_page).netloc
        self.client = httpx.AsyncClient(follow_redirects=True)

    async def fetch_content(self, url: str) -> str:
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.warning(f"⚠️ Could not fetch {url}: {e}")
            return ""

    async def collect_root_subpages(self) -> Dict[str, str]:
        html = await self.fetch_content(self.root_page)
        if not html:
            return {}

        soup = BeautifulSoup(html, "html.parser")
        links = soup.find_all("a", href=True)

        content_map = {}

        for link in links:
            href = link["href"]
            parsed_href = urlparse(href)

            if parsed_href.netloc == "" or parsed_href.netloc == self.domain:
                full_url = urljoin(self.root_page, href)
                logger.debug(f"Current subview detected: {full_url}")
                self.root_subpages.add(full_url)

        for url in self.root_subpages:
            content = await self.fetch_content(url)
            if content:
                soup = BeautifulSoup(content, "html.parser")
                main_heading = soup.find("h1")
                header_text = (
                    main_heading.get_text(strip=True) if main_heading else "Untitled"
                )

                content_map[url] = header_text

        return content_map

    async def close(
        self,
    ):  # TODO: remove close to embebd it directly into def __del__ as an abstract method
        await self.client.aclose()
