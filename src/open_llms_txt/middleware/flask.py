from __future__ import annotations
from functools import wraps
from typing import Callable, Set, Dict
from flask import Blueprint, current_app, request, Response
from urllib.parse import urljoin
from open_llms_txt.generator.html_to_md import HtmlToMdGenerator

# Only routes explicitly decorated can be mirrored
_ALLOWED_PATHS: Set[str] = set()
_DECORATED_ENDPOINTS: Set[str] = set()
_ENDPOINT_POLICY: Dict[str, bool] = {}
_BLUEPRINT_MOUNTED = False


def _ensure_blueprint(
    app,
    *,
    template_dir: str | None,
    template_name: str,
    url_prefix: str = "",
    blueprint_rule: str,
) -> None:
    if not template_name:
        raise ValueError("template_name is required")

    global _BLUEPRINT_MOUNTED
    if _BLUEPRINT_MOUNTED:
        return

    bp = Blueprint("llms_md", __name__, url_prefix=url_prefix)

    @bp.get(blueprint_rule)
    def _md_mirror(raw: str):
        target_path = f"/{raw}"

        # Checking allowed paths
        try:
            rules = list(current_app.url_map.iter_rules())
            _ALLOWED_PATHS.clear()
            for rule in rules:
                if rule.endpoint in _DECORATED_ENDPOINTS:
                    if (
                        not _ENDPOINT_POLICY.get(rule.endpoint, False)
                        and "<" in rule.rule
                    ):
                        continue
                    _ALLOWED_PATHS.add(rule.rule)
        except Exception:
            pass

        if target_path not in _ALLOWED_PATHS:
            return Response(
                "# 404\nMarkdown mirror not enabled for this path.\n",
                status=404,
                mimetype="text/markdown",
            )

        client = current_app.test_client()
        html_resp = client.get(target_path, headers={"Accept": "text/html"})
        if html_resp.status_code >= 400:
            return Response(
                f"# {html_resp.status_code}\nFailed to render `{target_path}`.\n",
                status=html_resp.status_code,
                mimetype="text/markdown",
            )

        html = html_resp.get_data(as_text=True)
        base = f"{request.scheme}://{request.host}"
        source_url = urljoin(base, target_path)

        generator = HtmlToMdGenerator(
            template_dir=template_dir, template_name=template_name
        )
        md = generator.render(
            html,
            root_url=base,
            source_url=source_url,
            allowed_paths=sorted(_ALLOWED_PATHS),
            mount_prefix=url_prefix,
        )
        return Response(md, mimetype="text/markdown; charset=utf-8")

    app.register_blueprint(bp)
    _BLUEPRINT_MOUNTED = True


def html2md(
    app,
    *,
    template_dir: str | None = None,
    template_name: str,
    mount_prefix: str = "",
    blueprint_rule: str = "/<path:raw>.html.md",
    allow_param_routes: bool = False,
) -> Callable[[Callable], Callable]:
    """
    Opt-in decorator: after decorating an endpoint, its Markdown mirror
    is available at '<mount_prefix>/<route>.html.md'.

    Example:
        @app.get("/pricing")
        @html2md(app, template_name="html_to_md.jinja")
        def pricing(): ...
        # -> /pricing (HTML)
        # -> /pricing.html.md (Markdown)  OR /.llms/pricing.html.md if mount_prefix="/.llms"
    """
    if not template_name:
        raise ValueError("template_name is required")

    _ensure_blueprint(
        app,
        template_dir=template_dir,
        template_name=template_name,
        url_prefix=mount_prefix or "",
        blueprint_rule=blueprint_rule,
    )

    def decorator(view_func: Callable) -> Callable:
        # Record that this endpoint has opted in (route may not be registered yet)
        endpoint = view_func.__name__
        _DECORATED_ENDPOINTS.add(endpoint)
        _ENDPOINT_POLICY[endpoint] = allow_param_routes

        @wraps(view_func)
        def wrapper(*args, **kwargs):
            return view_func(*args, **kwargs)

        return wrapper

    return decorator
