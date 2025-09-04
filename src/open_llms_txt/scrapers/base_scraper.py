# Copyright (c) 2025 Ricardo Espantaleón Pérez
# SPDX-License-Identifier: Apache-2.0

from abc import ABC, abstractmethod
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    def __init__(self, root: str):
        self.root_page = root
        self.root_subpages: set[str] = set()
        # TODO: add a template atribute to set the gross text from the typical llms.txt
        # TODO: predefined initially

        logger.debug(f"Setted root_page: {self.root_page}")

    @property
    def root_page(self):
        return self.__root_page

    @root_page.setter
    def root_page(self, root):
        self.__root_page = root.rstrip("/")

    @abstractmethod
    async def collect_root_subpages(self) -> Dict[str, str]:
        """Returns a dictionary of {url -> main header}"""
        pass

    @abstractmethod
    async def fetch_content(self, path: str) -> str:
        """Returns the HTML content from the path"""
        pass

    async def close(self) -> None:
        """Optional async cleanup. Default: no-op"""
        return
