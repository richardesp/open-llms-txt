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
_MANIFEST_BP_MOUNTED = False 


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


def llmstxt(
    app,
    *,
    template_dir: str | None = None,
    template_name: str,
    mount_prefix: str = "",
) -> Callable[[Callable], Callable]:
    """
    Decorator to expose an LLM-friendly manifest (llms.txt-style) on a chosen endpoint.
    It lists only routes that were explicitly decorated with @html2md, using the same
    allow-list logic (and honoring allow_param_routes).

    Example:
        @app.get("/")
        @llmstxt(app, template_name="llms.txt.jinja")
        def root_manifest():
            return ""  # body ignored; template-driven
    """
    if not template_name:
        raise ValueError("template_name is required")

    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            # Rebuild concrete allowed paths from decorated endpoints
            try:
                rules = list(current_app.url_map.iter_rules())
                _ALLOWED_PATHS.clear()
                for rule in rules:
                    ep = rule.endpoint
                    if ep in _DECORATED_ENDPOINTS:
                        if (not _ENDPOINT_POLICY.get(ep, False)) and "<" in rule.rule:
                            continue
                        _ALLOWED_PATHS.add(rule.rule)
            except Exception:
                # Keep going with whatever is currently in _ALLOWED_PATHS
                pass

            base = f"{request.scheme}://{request.host}"
            source_url = urljoin(base, request.path)

            generator = HtmlToMdGenerator(
                template_dir=template_dir, template_name=template_name
            )
           
            md = generator.render(
                "",
                root_url=base,
                source_url=source_url,
                allowed_paths=sorted(_ALLOWED_PATHS),
                mount_prefix=mount_prefix or "",
            )
            return Response(md, mimetype="text/markdown; charset=utf-8")

        return wrapper

    return decorator


def _ensure_manifest_blueprint(
    app,
    *,
    template_dir: str | None,
    template_name: str,
    manifest_path: str = "/llms.txt",
    mount_prefix: str = "",
    source_endpoint: str | None = None,
    source_rule: str | None = None,
) -> None:
    """
    Mount a manifest route (default '/llms.txt') that:
      1) rebuilds the same allow-list used by .html.md
      2) fetches the HTML of the *decorated* endpoint (index page)
      3) renders the manifest template *based on that HTML* (so its links drive the index)
    """
    if not template_name:
        raise ValueError("template_name is required")
    if not manifest_path.startswith("/"):
        raise ValueError("manifest_path must start with '/'")

    global _MANIFEST_BP_MOUNTED
    if _MANIFEST_BP_MOUNTED:
        return

    bp = Blueprint("llms_manifest", __name__)

    @bp.get(manifest_path)
    def _llms_manifest():
        # 1) Rebuild concrete allowed paths from decorated endpoints
        try:
            rules = list(current_app.url_map.iter_rules())
            _ALLOWED_PATHS.clear()
            for rule in rules:
                ep = rule.endpoint
                if ep in _DECORATED_ENDPOINTS:
                    if (not _ENDPOINT_POLICY.get(ep, False)) and "<" in rule.rule:
                        continue
                    _ALLOWED_PATHS.add(rule.rule)
        except Exception:
            pass

        # 2) Resolve the HTML source route for the manifest (the page you decorated)
        page_path = source_rule
        if not page_path and source_endpoint:
            try:
                for rule in current_app.url_map.iter_rules():
                    if rule.endpoint == source_endpoint and "<" not in rule.rule:
                        page_path = rule.rule
                        break
            except Exception:
                page_path = None

        if not page_path:
            return Response(
                "# 500\nUnable to resolve source page for llms.txt.\n",
                status=500,
                mimetype="text/markdown",
            )

        # Fetch that page's HTML
        client = current_app.test_client()
        html_resp = client.get(page_path, headers={"Accept": "text/html"})
        if html_resp.status_code >= 400:
            return Response(
                f"# {html_resp.status_code}\nFailed to render `{page_path}` for manifest.\n",
                status=html_resp.status_code,
                mimetype="text/markdown",
            )

        html = html_resp.get_data(as_text=True)
        base = f"{request.scheme}://{request.host}"
        # Use the *source page* as the canonical source_url for the manifest render
        source_url = urljoin(base, page_path)

        # 3) Render your llms.txt template based on that HTML (parser extracts links)
        generator = HtmlToMdGenerator(template_dir=template_dir, template_name=template_name)
        md = generator.render(
            html,
            root_url=base,
            source_url=source_url,
            allowed_paths=sorted(_ALLOWED_PATHS),
            mount_prefix=mount_prefix or "",
        )
        return Response(md, mimetype="text/markdown; charset=utf-8")

    app.register_blueprint(bp)
    _MANIFEST_BP_MOUNTED = True


def llmstxt(
    app,
    *,
    template_dir: str | None = None,
    template_name: str,
    mount_prefix: str = "",
    manifest_path: str = "/llms.txt",
) -> Callable[[Callable], Callable]:
    """
    Decorator that keeps the original endpoint as-is (serving HTML),
    and ALSO registers a separate manifest route (default: '/llms.txt').
    The manifest is rendered using the *HTML of the decorated endpoint* as input,
    so your template can build an index from that page's links.

    Usage:
        @app.get("/")
        @llmstxt(app, template_name="llms.txt.jinja", manifest_path="/llms.txt", mount_prefix="")
        def home():
            return render_template("home.html")
    """
    if not template_name:
        raise ValueError("template_name is required")

    def decorator(view_func: Callable) -> Callable:
        # Discover a concrete rule for the decorated HTML endpoint (prefer non-parameterized)
        endpoint = view_func.__name__
        discovered_rule = None
        try:
            for rule in app.url_map.iter_rules():
                if rule.endpoint == endpoint and "<" not in rule.rule:
                    discovered_rule = rule.rule
                    break
        except Exception:
            discovered_rule = None

        _ensure_manifest_blueprint(
            app,
            template_dir=template_dir,
            template_name=template_name,
            manifest_path=manifest_path,
            mount_prefix=mount_prefix,
            source_endpoint=endpoint,
            source_rule=discovered_rule,
        )

        @wraps(view_func)
        def wrapper(*args, **kwargs):
            # Return the original HTML view unchanged
            return view_func(*args, **kwargs)

        return wrapper

    return decorator