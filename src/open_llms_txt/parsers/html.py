from bs4 import BeautifulSoup
from typing import Dict, Any, List

def parse_html_to_json(html: str, **metadata) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")

    def clean(text: str) -> str:
        return text.strip() if text else ""

    links: List[Dict[str, str]] = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a.get("href").strip()
        if not href or href.startswith("#"):
            continue

        text = clean(a.get_text())
        if not text or len(text) < 3:
            continue

        if href not in seen:
            links.append({"text": text, "href": href})
            seen.add(href)

    return {
        "metadata": metadata,  
        "title": clean(soup.title.string if soup.title else ""),
        "h1": clean(soup.find("h1").get_text() if soup.find("h1") else ""),
        "headings": [clean(tag.get_text()) for tag in soup.find_all(["h2", "h3"])],
        "paragraphs": [clean(p.get_text()) for p in soup.find_all("p") if clean(p.get_text())],
        "links": links,
    }
