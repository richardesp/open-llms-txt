from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse

import click

from open_llms_txt.generator.html_to_md import HtmlToMdGenerator
from open_llms_txt.scraper.web_scraper import WebScraper


def _read_stdin() -> Optional[str]:
    """Read HTML from stdin if piped in, return None when nothing is provided."""
    # Avoid swallowing unexpected errors: reading stdin shouldn't raise in normal CLIs.
    if sys.stdin is not None and not sys.stdin.isatty():
        data = sys.stdin.read()
        data = data.strip()
        return data or None
    return None


async def _fetch(url: str) -> str:
    """Fetch HTML from a remote URL asynchronously."""
    scraper = WebScraper(url)
    try:
        return await scraper.fetch_content(url)
    finally:
        # Ensure network resources are released
        await scraper.close()


def _split_url(url: Optional[str]) -> Tuple[str, str]:
    """
    Given a URL (or None), return (root_url, source_url).
      - root_url: 'scheme://host'
      - source_url: full URL
    If url is None or invalid, returns ("", "") or ("", original_string) respectively.
    """
    if not url:
        return "", ""
    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}", url
    # Not a valid absolute URL; still return the provided string as source_url
    return "", url


def _read_file(path: Path) -> str:
    """Read a local HTML file as UTF-8 with clear error messages."""
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        raise click.FileError(str(path), hint="File not found.") from e
    except PermissionError as e:
        raise click.FileError(
            str(path), hint="Insufficient permissions to read the file."
        ) from e
    except OSError as e:
        raise click.FileError(str(path), hint=str(e)) from e


def _write_file(path: Path, content: str) -> None:
    """Write output to a file as UTF-8, creating parent dirs if needed."""
    try:
        if parent := path.parent:
            parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
    except PermissionError as e:
        raise click.FileError(
            str(path), hint="Insufficient permissions to write the file."
        ) from e
    except OSError as e:
        raise click.FileError(str(path), hint=str(e)) from e


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--url",
    type=str,
    help="Remote URL to fetch (also used as canonical URL metadata).",
)
@click.option(
    "--file",
    "file_",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    help="Local HTML file to read.",
)
@click.option(
    "--template-name",
    required=True,
    type=str,
    help="Jinja template name (e.g. 'scraper_template.jinja').",
)
@click.option(
    "--template-dir",
    type=click.Path(
        exists=True, file_okay=False, dir_okay=True, readable=True, path_type=Path
    ),
    help="Directory containing Jinja templates.",
)
@click.option(
    "--out",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    help="Write result to file instead of stdout.",
)
@click.version_option(message="open-llms-txt %(version)s")
def main(
    url: Optional[str],
    file_: Optional[Path],
    template_name: str,
    template_dir: Optional[Path],
    out: Optional[Path],
) -> None:
    """
    Render HTML → Markdown for LLMs based on the llms.txt standard using
    Jinja templates.

    Input precedence:

    1) stdin (when piped)
    2) --file
    3) --url

    Examples:

    cat page.html | open-llms-txt --template-name scraper_template.jinja
    open-llms-txt --file page.html --template-name scraper_template.jinja
    open-llms-txt --url https://example.com --template-name scraper_template.jinja
    """
    html: Optional[str] = _read_stdin()

    if html is None and file_ is not None:
        html = _read_file(file_)

    if html is None and url:
        try:
            html = asyncio.run(_fetch(url))
        except Exception as e:
            raise click.ClickException(
                f"[open-llms-txt] fetch error for URL '{url}': {e}"
            ) from e

    if not html:
        raise click.UsageError(
            "No input HTML provided. Use stdin pipe, --url, or --file."
        )

    root_url, source_url = _split_url(url)

    try:
        generator = HtmlToMdGenerator(
            template_dir=str(template_dir) if template_dir is not None else None,
            template_name=template_name,
        )
        md = generator.render(
            html,
            root_url=root_url,
            source_url=source_url,
        )
    except Exception as e:
        raise click.ClickException(f"[open-llms-txt] render error: {e}") from e

    if out:
        _write_file(out, md)
        click.echo(f"Wrote Markdown to: {out}", err=True)
        return

    # Use click.echo to respect environment encodings and handle TTYs well
    click.echo(md, nl=not md.endswith("\n"))


if __name__ == "__main__":
    main()
