# Copyright (c) 2025 Ricardo Espantaleón Pérez
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

import pytest

from open_llms_txt.scrapers.local_scraper import LocalScraper


@pytest.mark.asyncio
async def test_fetch_content_reads_file(tmp_path: Path):
    f = tmp_path / "page.html"
    f.write_text("<html><body><h1>Hi</h1></body></html>", encoding="utf-8")

    scraper = LocalScraper(str(f))
    out = await scraper.fetch_content(str(f))
    assert "<h1>Hi</h1>" in out


@pytest.mark.asyncio
async def test_fetch_content_missing_file_logs_and_returns_empty(
    tmp_path: Path, caplog
):
    missing = tmp_path / "nope.html"
    scraper = LocalScraper(str(missing))

    with caplog.at_level("WARNING"):
        out = await scraper.fetch_content(str(missing))
    assert out == ""
    assert any(
        "Could not read local file" in rec.getMessage() for rec in caplog.records
    )


@pytest.mark.asyncio
async def test_collect_root_subpages_includes_root_and_valid_subpages(tmp_path: Path):
    # Files
    root = tmp_path / "index.html"
    about = tmp_path / "about.html"
    contact = tmp_path / "contact.html"
    image = tmp_path / "logo.png"  # non-html -> ignored
    missing = tmp_path / "missing.html"  # not created -> ignored

    root.write_text(
        """
        <html><body>
          <h1>Home</h1>
          <a href="#section">anchor</a>
          <a href="about.html">About us</a>
          <a href="contact.html">Contact</a>
          <a href="missing.html">Missing</a>
          <a href="logo.png">Logo</a>
        </body></html>
        """,
        encoding="utf-8",
    )
    about.write_text("<html><body><h1>About Title</h1></body></html>", encoding="utf-8")
    contact.write_text(
        "<html><body><p>Contact page</p></body></html>", encoding="utf-8"
    )
    image.write_bytes(b"\x89PNG\r\n\x1a\n...")

    scraper = LocalScraper(str(root))
    content_map = await scraper.collect_root_subpages()

    # Should include absolute, resolved paths as keys
    expected_keys = {str(p.resolve()) for p in (root, about, contact)}
    assert set(content_map.keys()) == expected_keys

    # Values are extracted H1s
    assert content_map[str(about.resolve())] == "About Title"
    assert content_map[str(contact.resolve())] == "Untitled"
    assert content_map[str(root.resolve())] == "Home"

    # Ensure ignored targets are not added as subpages
    anchor_target = (root.parent / "#section").resolve()
    assert str(anchor_target) not in scraper.root_subpages
    assert str(image.resolve()) not in scraper.root_subpages
    assert str(missing.resolve()) not in scraper.root_subpages


@pytest.mark.asyncio
async def test_collect_root_subpages_ignores_weird_or_non_html_hrefs(tmp_path: Path):
    root = tmp_path / "index.html"
    weird = '["not-a-string"]'  # weird literal -> ignored (won't exist / not .html)
    root.write_text(
        f"""
        <html><body>
          <h1>Root</h1>
          <a href="{weird}">Weird</a>
          <a href="file.txt">Not html</a>
          <a href="#top">Anchor</a>
        </body></html>
        """,
        encoding="utf-8",
    )

    scraper = LocalScraper(str(root))
    content_map = await scraper.collect_root_subpages()

    # Only the root should be included
    root_key = str(root.resolve())
    assert set(content_map.keys()) == {root_key}
    assert content_map[root_key] == "Root"

    # And none of the ignored targets should be tracked as subpages
    weird_path = (root.parent / '["not-a-string"]').resolve()
    txt_path = (root.parent / "file.txt").resolve()
    anchor_target = (root.parent / "#top").resolve()
    assert root_key in scraper.root_subpages
    assert str(weird_path) not in scraper.root_subpages
    assert str(txt_path) not in scraper.root_subpages
    assert str(anchor_target) not in scraper.root_subpages


@pytest.mark.asyncio
async def test_collect_root_subpages_empty_root_returns_empty_map(tmp_path: Path):
    root = tmp_path / "empty.html"
    root.write_text("", encoding="utf-8")

    scraper = LocalScraper(str(root))
    out = await scraper.collect_root_subpages()
    assert out == {}
