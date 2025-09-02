# src/open_llms_txt/web/local_scraper.py

from pathlib import Path
from typing import Dict
from bs4 import BeautifulSoup, Tag
from .base_scraper import BaseScraper
import logging

logger = logging.getLogger(__name__)


class LocalScraper(BaseScraper):
    def __init__(self, root: str):
        super().__init__(root)
        self.root_file = Path(root).resolve()
        self.local_root_url = self.root_file.as_uri()
        self.base_dir = self.root_file.parent
        self.root_subpages = set()

    async def fetch_content(self, path: str) -> str:
        try:
            content = Path(path).read_text(encoding="utf-8")
            return content
        except Exception as e:
            logger.warning(f"⚠️ Could not read local file {path}: {e}")
            return ""

    async def collect_root_subpages(self) -> Dict[str, str]:
        content_map = {}

        root_html = await self.fetch_content(str(self.root_file))
        if not root_html:
            return {}

        soup = BeautifulSoup(root_html, "html.parser")
        links = soup.find_all("a", href=True)

        for link in links:
            if isinstance(link, Tag) and isinstance(link.get("href"), str):
                href: str = str(link["href"])
                target_path = (self.base_dir / href).resolve()

                if target_path.suffix == ".html" and target_path.exists():
                    logger.debug(f"Current subview detected: {target_path}")
                    self.root_subpages.add(str(target_path))

        # Always include the root file itself
        self.root_subpages.add(str(self.root_file))

        for file_path in self.root_subpages:
            html = await self.fetch_content(file_path)
            if html:
                soup = BeautifulSoup(html, "html.parser")
                main_heading = soup.find("h1")
                header_text = (
                    main_heading.get_text(strip=True) if main_heading else "Untitled"
                )

                content_map[file_path] = header_text

        return content_map
