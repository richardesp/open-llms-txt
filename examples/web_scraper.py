import asyncio
import logging

from open_llms_txt.scrapers.web_scraper import WebScraper
from open_llms_txt.generators.html_to_md import HtmlToMdGenerator

logging.basicConfig()
logging.getLogger("open_llms_txt").setLevel(logging.DEBUG)


async def main():
    # scraper = WebScraper("https://research.ibm.com/")
    # pages = await scraper.collect_root_subpages()
    # generator = HtmlToMdGenerator()

    # for p in pages:
    #    print(f"{p}:\n{generator.render(await scraper.fetch_content(p),
    #          root_url=scraper.root_page, source_url=p)}")
    #    break
    root_url = "https://research.ibm.com/"
    url = "https://research.ibm.com/"
    scraper = WebScraper(url)
    generator = HtmlToMdGenerator(template_name="scraper_template.jinja")
    print(
        generator.render(await scraper.fetch_content(url), root_url=root_url, source_url=url)
    )

    await scraper.close()


if __name__ == "__main__":
    asyncio.run(main())
