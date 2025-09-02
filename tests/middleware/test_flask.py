from __future__ import annotations

from pathlib import Path

from flask import Flask, render_template_string
import pytest

import open_llms_txt.middleware.flask as mw
from open_llms_txt.middleware.flask import html2md, llmstxt


@pytest.fixture(autouse=True)
def reset_middleware_state():
    """Reset module-level global state so tests don't interfere with each other"""

    mw._ALLOWED_PATHS.clear()
    mw._DECORATED_ENDPOINTS.clear()
    mw._ENDPOINT_POLICY.clear()
    mw._BLUEPRINT_MOUNTED = False
    mw._MANIFEST_BP_MOUNTED = False


@pytest.fixture
def tmp_templates(tmp_path: Path):
    (tmp_path / "html_to_md.jinja").write_text(
        "# {{ title }}\n{{ h1 }}\n", encoding="utf-8"
    )

    (tmp_path / "llms.txt.jinja").write_text(
        "SOURCE={{ metadata.source_url }}\n"
        "ALLOWED={{ metadata.allowed_paths|join(',') }}\n",
        encoding="utf-8",
    )
    return tmp_path


def make_app() -> Flask:
    app = Flask(__name__)
    app.testing = True
    return app


def test_html2md_exposes_markdown_for_decorated_endpoint(tmp_templates: Path):
    app = make_app()

    @app.get("/pricing")
    @html2md(
        app,
        template_dir=str(tmp_templates),
        template_name="html_to_md.jinja",
    )
    def pricing():
        # a simple page with <title> and <h1>
        return render_template_string(
            (
                "<html><head><title>Pricing</title></head><body>"
                "<h1>Our Pricing</h1>"
                "</body></html>"
            )
        )

    client = app.test_client()

    # HTML works
    html_res = client.get("/pricing")
    assert html_res.status_code == 200
    assert b"Our Pricing" in html_res.data

    # Markdown mirror works
    md_res = client.get("/pricing.html.md")
    assert md_res.status_code == 200
    assert md_res.mimetype.startswith("text/markdown")  # type: ignore
    body = md_res.get_data(as_text=True)
    assert "# Pricing" in body
    assert "Our Pricing" in body


def test_html2md_denies_undecorated_endpoint(tmp_templates: Path):
    app = make_app()

    @app.get("/decorated")
    @html2md(app, template_dir=str(tmp_templates), template_name="html_to_md.jinja")
    def decorated():
        return (
            "<html><head><title>OK</title></head><body><h1>Decorated</h1></body></html>"
        )

    @app.get("/plain")
    def plain():
        return "<html><body><h1>Plain</h1></body></html>"

    client = app.test_client()

    # The undecorated endpoint's mirror should 404
    res = client.get("/plain.html.md")
    assert res.status_code == 404
    assert "Markdown mirror not enabled" in res.get_data(as_text=True)


def test_html2md_propagates_source_error(tmp_templates: Path):
    app = make_app()

    @app.get("/broken")
    @html2md(app, template_dir=str(tmp_templates), template_name="html_to_md.jinja")
    def broken():
        return ("oops", 500)

    client = app.test_client()
    res = client.get("/broken.html.md")
    assert res.status_code == 500
    body = res.get_data(as_text=True)
    assert "# 500" in body
    assert "Failed to render `/broken`." in body


def test_html2md_with_mount_prefix(tmp_templates: Path):
    app = make_app()

    @app.get("/features")
    @html2md(
        app,
        template_dir=str(tmp_templates),
        template_name="html_to_md.jinja",
        mount_prefix="/.llms",  # serve mirrors under this prefix
    )
    def features():
        return (
            "<html><head><title>Features</title></head>",
            "<body><h1>All Features</h1></body></html>",
        )

    client = app.test_client()

    # Mirror path is prefixed
    res = client.get("/.llms/features.html.md")
    assert res.status_code == 200
    assert "# Features" in res.get_data(as_text=True)


def test_llmstxt_renders_manifest_from_decorated_source(tmp_templates: Path):
    app = make_app()

    @app.get("/")
    @llmstxt(
        app,
        template_dir=str(tmp_templates),
        template_name="llms.txt.jinja",
        mount_prefix="/.llms",
        manifest_path="/llms.txt",
    )
    def home():
        return (
            "<html><head><title>Home</title></head><body><h1>Welcome</h1></body></html>"
        )

    # Another page that will appear in the allow-list (and have a mirror)
    @app.get("/about")
    @html2md(app, template_dir=str(tmp_templates), template_name="html_to_md.jinja")
    def about():
        return (
            "<html><head><title>About</title></head>",
            "<body><h1>About us</h1></body></html>",
        )

    client = app.test_client()

    # Manifest is served and includes the source URL and allowed path(s)
    res = client.get("/llms.txt")
    assert res.status_code == 200
    assert res.mimetype.startswith("text/markdown")  # type: ignore
    text = res.get_data(as_text=True)

    # SOURCE should be the canonical URL for the decorated page ("/")
    assert "SOURCE=http://" in text or "SOURCE=https://" in text
    # ALLOWED contains concrete rules ("/" will not be listed unless
    # decorated with html2md. "/about" should be there)
    assert "/about" in text


def test_llmstxt_returns_500_if_source_unresolvable(tmp_templates: Path):
    """If we can't resolve a non-parameterized rule for the decorated
    endpoint, 500 is returned."""
    app = make_app()

    @app.get("/item/<id>")
    @llmstxt(app, template_dir=str(tmp_templates), template_name="llms.txt.jinja")
    def item(id: str):  # noqa: ARG001
        return "<html><body><h1>Item</h1></body></html>"

    client = app.test_client()
    res = client.get("/llms.txt")

    assert res.status_code == 500
    assert "Unable to resolve source page for llms.txt." in res.get_data(as_text=True)
