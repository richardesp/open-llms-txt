from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from typing import Optional

from ..parsers.html import parse_html_to_json


class HtmlToMdGenerator:
    def __init__(self, template_dir: Optional[str] = None, template_name: str = "html_to_md.jinja"):
        if template_dir is None:
            # Default: package templates folder (e.g., src/open_llms_txt/templates)
            template_dir = Path(__file__).parent.parent / "templates"

        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True
        )
        self.template = self.env.get_template(template_name)

    def render(self, html: str, root_url: str = None, source_url: str = None) -> str:
        context = parse_html_to_json(html, root_url=root_url, source_url=source_url)
        return self.template.render(engine="jinja2", **context) # TODO: externalize the engine param with a predefined ENUM clause
