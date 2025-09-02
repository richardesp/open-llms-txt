import pytest

from open_llms_txt.parsers.html import parse_html_to_json


def test_metadata_passthrough():
    html = "<html><head><title> Sample </title></head><body></body></html>"
    out = parse_html_to_json(html, source="unit-test", lang="en")
    assert out["metadata"] == {"source": "unit-test", "lang": "en"}


def test_title_and_h1_cleaning_and_extraction():
    html = """
    <html>
      <head><title>
        My  Page Title
      </title></head>
      <body>
        <h1>
           Welcome to  My Site
        </h1>
      </body>
    </html>
    """
    out = parse_html_to_json(html)
    assert out["title"] == "My  Page Title".strip()
    assert out["h1"] == "Welcome to  My Site".strip()


def test_title_missing_h1_missing_results_in_empty_strings():
    html = "<html><head></head><body></body></html>"
    out = parse_html_to_json(html)
    assert out["title"] == ""
    assert out["h1"] == ""


def test_headings_collect_h2_and_h3_in_document_order():
    html = """
    <html><body>
      <h2>Intro</h2>
      <h3>Background</h3>
      <h2>Usage</h2>
      <h3>Details</h3>
      <h4>Ignored</h4>
    </body></html>
    """
    out = parse_html_to_json(html)
    assert out["headings"] == ["Intro", "Background", "Usage", "Details"]


def test_paragraphs_are_cleaned_and_empty_removed():
    html = """
    <html><body>
      <p>  First paragraph.  </p>
      <p>     </p>
      <p>
          Second paragraph with
          spaces.
      </p>
      <div>Not a paragraph</div>
    </body></html>
    """
    out = parse_html_to_json(html)
    assert out["paragraphs"] == [
        "First paragraph.",
        "Second paragraph with\n          spaces.",
    ]


def test_links_filter_out_anchors_and_short_text_and_deduplicate():
    html = """
    <html><body>
      <a href="#section">Anchor link</a>
      <a href="  /about  ">  Ab  </a>     <!-- text < 3 chars after strip -->
      <a href="/about">About us</a>
      <a href="/about">About us (duplicate href, should dedupe)</a>
      <a href="/contact"> Contact </a>
    </body></html>
    """
    out = parse_html_to_json(html)
    # Order preserved; no anchors; no short text ("Ab"); dedup by href
    assert out["links"] == [
        {"text": "About us", "href": "/about"},
        {"text": "Contact", "href": "/contact"},
    ]


@pytest.mark.parametrize(
    "raw,expected",
    [
        (
            """<html><head><title>  Title  </title></head><body>
                <h1> H1 </h1></body></html>""",
            ("Title", "H1"),
        ),
        (
            "<html><head></head><body><h1>H1 only</h1></body></html>",
            ("", "H1 only"),
        ),
        (
            "<html><head><title>Only Title</title></head><body></body></html>",
            ("Only Title", ""),
        ),
    ],
)
def test_title_h1_variations(raw, expected):
    out = parse_html_to_json(raw)
    assert (out["title"], out["h1"]) == expected


def test_empty_document_returns_minimal_structure():
    out = parse_html_to_json("")
    assert out["title"] == ""
    assert out["h1"] == ""
    assert out["headings"] == []
    assert out["paragraphs"] == []
    assert out["links"] == []
    assert "metadata" in out


def test_whitespace_and_unicode_are_preserved_after_strip():
    html = """
    <html><head><title> Café Title </title></head>
    <body>
      <h1>  Привет  </h1>
      <p>  Hello World &nbsp;  </p>
      <a href="/ñandú">  Ñandú Docs  </a>
    </body></html>
    """
    out = parse_html_to_json(html, lang="es")
    assert out["title"] == "Café Title".strip()
    assert out["h1"] == "Привет".strip()
    # paragraph keeps inner non-breaking spaces once converted by BeautifulSoup get_text
    assert any("Hello" in p for p in out["paragraphs"])
    assert out["links"][0]["href"] == "/ñandú"
    assert out["links"][0]["text"] == "Ñandú Docs".strip()
