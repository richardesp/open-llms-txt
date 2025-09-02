import asyncio
import logging

from open_llms_txt.scraper.local_scraper import LocalScraper
from open_llms_txt.generator.html_to_md import HtmlToMdGenerator

logging.basicConfig()
logging.getLogger("open_llms_txt").setLevel(logging.DEBUG)


async def main():
    scraper = LocalScraper("./static_site/index.html")
    generator = HtmlToMdGenerator(template_name="scraper_template.jinja")

    raw_html = await scraper.fetch_content(scraper.root_file)
    md = generator.render(raw_html, root_url=scraper.local_root_url)
    
    print(md)


if __name__ == "__main__":
    asyncio.run(main())
