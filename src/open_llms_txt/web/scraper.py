import httpx
from bs4 import BeautifulSoup
import os
from pathlib import Path

from urllib.parse import urlparse, urljoin
from typing import List, Set
import logging
from markdownify import markdownify as md


logger = logging.getLogger(__name__)

class Scraper:
    def __init__(self, root_url: str):
        self.root_url = root_url.rstrip("/")
        self.domain = urlparse(root_url).netloc
        self.subpages: Set[str] = set()
        self.visited: Set[str] = set()
        self.client = httpx.AsyncClient(follow_redirects=True)

    async def fetch(self, url: str) -> str:
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.text
        except httpx.RequestError as e:
            print(f"⚠️ Error fetching {url}: {e}")
            return ""

    async def html_to_markdown(self, html_content: str, filename: str, output_dir: str = "md_views"):
        os.makedirs(output_dir, exist_ok=True)
        markdown = md(html_content, heading_style="ATX")

        output_path = Path(output_dir) / f"{filename}.html.md"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown)
        logger.debug(f"Saved markdown to: {output_path}")

    async def crawl_html_md_links(self) -> List[str]:
        """
        Fetch root page and look for .html.md links to include in llms.txt.
        """
        logger.debug(f"Fetching content from: {self.root_url}")
        
        content = await self.fetch(self.root_url)
        logger.debug(f"Content retrieved from root_url: {content[:50]}...")
        
        if not content:
            return []

        logger.debug(f"Scraping website with BeautifulSoup")
        soup = BeautifulSoup(content, "html.parser")
        links = soup.find_all("a", href=True)

        for link in links:
            href = link["href"]
            parsed_href = urlparse(href)

            if parsed_href.netloc == "" or parsed_href.netloc == self.domain:
                full_url = urljoin(self.root_url, href)

                logger.debug(f"Current view to process: {full_url}")
                self.subpages.add(full_url)

                html = await self.fetch(full_url)
                if html:
                    # Use URL path as filename, safely
                    filename = Path(urlparse(full_url).path).stem or "index"
                    await self.html_to_markdown(html, filename)
                
        return list(self.subpages)

    async def close(self):
        await self.client.aclose()
