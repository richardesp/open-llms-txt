import asyncio
import logging

from open_llms_txt.scraper.local_scraper import LocalScraper
from open_llms_txt.generator.html_to_md import HtmlToMdGenerator

logging.basicConfig()
logging.getLogger("open_llms_txt").setLevel(logging.DEBUG)


async def main():
    scraper = LocalScraper("./site/index.html")
    views = await scraper.collect_root_subpages()
    generator = HtmlToMdGenerator()

    for p in views:
        print(f"{p}:\n{generator.render(await scraper.fetch_content(p))}")
        break


if __name__ == "__main__":
    asyncio.run(main())
