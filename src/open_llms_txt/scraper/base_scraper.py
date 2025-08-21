from abc import ABC, abstractmethod
from typing import Dict

class BaseScraper(ABC):
    def __init__(self, root: str):
        self.root = root.rstrip("/")
        self.subpages = set()

    @abstractmethod
    async def collect_views(self) -> Dict[str, str]:
        """Returns a dictionary of {url -> html_content}"""
        pass

    @abstractmethod
    async def _fetch(self, path: str) -> str:
        pass
