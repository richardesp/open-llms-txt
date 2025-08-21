from pathlib import Path
from .base_scraper import BaseScraper
import logging

logger = logging.getLogger(__name__)

class LocalScraper(BaseScraper):
    def __init__(self, root: str):
        super().__init__(root)
        self.root_path = Path(root)

    async def _fetch(self, path: str) -> str:
        try:
            content = Path(path).read_text(encoding="utf-8")
            logger.debug(f"📄 Loaded local HTML file: {path}")
            return content
        except Exception as e:
            logger.warning(f"❌ Failed to read local file {path}: {e}")
            return ""

    async def collect_views(self):
        html_files = list(self.root_path.rglob("*.html"))
        for html_file in html_files:
            logger.debug(f"Local view to process: {html_file}")
            self.subpages.add(str(html_file.resolve()))

        return list(self.subpages)
