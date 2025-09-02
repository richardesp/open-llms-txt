from enum import Enum


class TemplateEngine(str, Enum):
    JINJA2 = "jinja2"
    NUNJUCKS = "nunjucks"
