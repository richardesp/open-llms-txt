from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from typing import Optional

from ..parsers.html import parse_html_to_json
from .template_engine import TemplateEngine


class HtmlToMdGenerator:
    def __init__(
        self,
        template_dir: Optional[str] = None,
        template_name: str = "html_to_md.jinja",
        engine: TemplateEngine = TemplateEngine.JINJA2,
    ):
        if template_dir is None:
            # Default: package templates folder (e.g., src/open_llms_txt/templates)
            template_dir = str(Path(__file__).parent.parent / "templates")

        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.template = self.env.get_template(template_name)
        self.engine: TemplateEngine = engine

    def render(self, html: str, **metadata) -> str:
        context = parse_html_to_json(html, **metadata)
        print(context)
        return self.template.render(engine=self.engine, **context)
