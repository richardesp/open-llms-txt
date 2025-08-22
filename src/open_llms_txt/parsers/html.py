import datetime
from bs4 import BeautifulSoup
from typing import Dict, Any

from urllib.parse import urljoin

def parse_html_to_json(html: str, root_url: str = None, source_url: str = None) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")

    def clean(text: str) -> str:
        return text.strip() if text else ""

    links = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a.get("href").strip()
        
        if href.startswith("#"):
            continue
        
        # Own view from the root page (.html.md standard applied)
        if not href.startswith('http'):
            href = urljoin(root_url, href)
            
            if not href.endswith('.html'):
                href += '.html'
                
            href += '.md'
        
        text = clean(a.get_text())

        if not href or href in seen:
            continue
        if len(text) < 3: # Avoid noise
            continue

        links.append({"text": text, "href": href})
        seen.add(href)

    metadata = {
        "root_url": root_url or "",
        "source_url": source_url or ""
    }

    return {
        "metadata": metadata,
        "title": clean(soup.title.string if soup.title else ""),
        "h1": clean(soup.find("h1").get_text() if soup.find("h1") else ""),
        "headings": [clean(tag.get_text()) for tag in soup.find_all(["h2", "h3"])],
        "paragraphs": [clean(p.get_text()) for p in soup.find_all("p") if clean(p.get_text())],
        "links": links,
    }
