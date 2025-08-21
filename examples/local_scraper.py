import asyncio
import logging

from open_llms_txt.scraper.local_scraper import LocalScraper

logging.basicConfig()
logging.getLogger("open_llms_txt").setLevel(logging.DEBUG)


async def main():
    scraper = LocalScraper("./site/index.html")
    views = await scraper.collect_root_subpages()
    print("📄 Discovered .html.md pages from root:")

    for p in views:
        print(f"{p}: {views[p]}...\n")


if __name__ == "__main__":
    asyncio.run(main())
