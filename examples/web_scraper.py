import asyncio
import logging

from open_llms_txt.scraper.web_scraper import WebScraper

logging.basicConfig()
logging.getLogger("open_llms_txt").setLevel(logging.DEBUG)

async def main():
    scraper = WebScraper("https://research.ibm.com/")
    pages = await scraper.collect_views()
    print("📄 Discovered .html.md pages:")
    for p in pages:
        print(f"{p}: {pages[p][:100]}...\n")
    await scraper.close()

if __name__ == "__main__":
    asyncio.run(main())
