from bs4 import BeautifulSoup, Tag
from typing import Dict, Any, List


def parse_html_to_json(html: str, **metadata) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")

    def clean(text: str | None) -> str:
        return text.strip() if text else ""

    links: List[Dict[str, str]] = []
    seen = set()
    for a in soup.find_all("a", href=True):
        if not isinstance(a, Tag):
            continue

        href_raw = a.get("href")
        if not isinstance(href_raw, str):
            continue

        href = href_raw.strip()
        if not href or href.startswith("#"):
            continue

        text = clean(a.get_text())
        if not text or len(text) < 3:
            continue

        if href not in seen:
            links.append({"text": text, "href": href})
            seen.add(href)

    title = clean(soup.title.string if soup.title and soup.title.string else "")
    h1_tag = soup.find("h1")
    h1 = clean(h1_tag.get_text() if h1_tag else "")

    headings = [
        clean(tag.get_text())
        for tag in soup.find_all(["h2", "h3"])
        if isinstance(tag, Tag)
    ]
    paragraphs = [
        clean(p.get_text())
        for p in soup.find_all("p")
        if isinstance(p, Tag) and clean(p.get_text())
    ]

    return {
        "metadata": metadata,
        "title": title,
        "h1": h1,
        "headings": headings,
        "paragraphs": paragraphs,
        "links": links,
    }
