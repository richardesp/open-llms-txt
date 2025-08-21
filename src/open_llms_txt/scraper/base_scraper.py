from abc import ABC, abstractmethod
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    def __init__(self, root: str):
        self.root_page = root
        self.root_subpages = set()

        logger.debug(f"Setted root_page: {self.root_page}")

    @property
    def root_page(self):
        return self.__root_page

    @root_page.setter
    def root_page(self, root):
        self.__root_page = root.rstrip("/")

    @abstractmethod
    async def collect_root_subpages(self) -> Dict[str, str]:
        """Returns a dictionary of {url -> html_content}"""
        pass

    @abstractmethod
    async def fetch_content(self, path: str) -> str:
        pass
