from pathlib import Path

import pytest

from open_llms_txt.generators.html_to_md import HtmlToMdGenerator


def _write_template(dir_: Path, name: str = "html_to_md.jinja") -> Path:
    """
    Minimal deterministic Jinja2 template so we don't depend on
    the package's real template. Returns the path to the template file.
    """
    template = (
        "# {{ title }}\n"
        "{{ h1 }}\n"
        "{% for h in headings %}## {{ h }}\n{% endfor %}"
        "{% for p in paragraphs %}{{ p }}\n{% endfor %}"
        "{% for l in links %}- [{{ l.text }}]({{ l.href }})\n{% endfor %}"
        "-- {{ metadata.source }} | {{ metadata.lang }}\n"
    )
    path = dir_ / name
    path.write_text(template, encoding="utf-8")
    return path


def _sample_html() -> str:
    return """
    <html>
      <head><title> Sample Title </title></head>
      <body>
        <h1> Welcome Home </h1>
        <h2>Intro</h2>
        <h3>Background</h3>

        <p> First paragraph. </p>
        <p>   </p>
        <p> Second paragraph here. </p>

        <a href="#anchor">Anchor (ignored)</a>
        <a href="/about">About us</a>
        <a href="/c">c</a>  <!-- too short, ignored by parse_html_to_json -->
        <a href="/contact"> Contact </a>
      </body>
    </html>
    """


@pytest.mark.parametrize("custom_name", [None, "custom_template.jinja"])
def test_render_with_custom_template_and_metadata(tmp_path: Path, custom_name):
    if custom_name:
        _write_template(tmp_path, name=custom_name)
        gen = HtmlToMdGenerator(template_dir=str(tmp_path), template_name=custom_name)
    else:
        _write_template(tmp_path)  # writes html_to_md.jinja
        gen = HtmlToMdGenerator(template_dir=str(tmp_path))

    html = _sample_html()

    # Act
    out = gen.render(html, source="unit-test", lang="en")

    # Assert: title & h1
    assert "# Sample Title" in out
    assert "Welcome Home" in out

    # headings
    assert "## Intro" in out
    assert "## Background" in out

    # paragraphs
    assert "First paragraph." in out
    assert "Second paragraph here." in out

    # links
    assert "- [About us](/about)" in out
    assert "- [Contact](/contact)" in out
    assert "#anchor" not in out
    assert "](/c)" not in out

    # metadata shows up
    assert "-- unit-test | en" in out


def test_render_handles_empty_minimal_html(tmp_path: Path):
    _write_template(tmp_path)
    gen = HtmlToMdGenerator(template_dir=str(tmp_path))

    html = "<html><head></head><body></body></html>"

    # Act
    out = gen.render(html, source="smoke", lang="xx")

    # Assert: no crash, structure renders with empty fields/lists
    assert "# " in out

    # metadata rendered
    assert "-- smoke | xx" in out

    # No links or headings/paragraphs emitted
    assert "](" not in out
