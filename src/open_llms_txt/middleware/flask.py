from __future__ import annotations

from functools import wraps
from typing import Callable, Dict, Set
from urllib.parse import urljoin

from flask import Blueprint, Response, current_app, request

from open_llms_txt.generator.html_to_md import HtmlToMdGenerator

# Only routes explicitly decorated can be mirrored
_ALLOWED_PATHS: Set[str] = set()
_DECORATED_ENDPOINTS: Set[str] = set()
_ENDPOINT_POLICY: Dict[str, bool] = {}
_BLUEPRINT_MOUNTED = False
_MANIFEST_BP_MOUNTED = False


def _ensure_html2md_blueprint(
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

    bp = Blueprint("html2md_manifest", __name__, url_prefix=url_prefix)

    @bp.get(blueprint_rule)
    def _html2md_manifest(raw: str):
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
    Opt-in decorator that exposes a Markdown "mirror" for a Flask endpoint.

    After decorating an endpoint, a Markdown version of its HTML response becomes
    available under a parallel route that ends with ``.html.md``. Only endpoints
    explicitly decorated with ``@html2md`` are eligible to be mirrored.

    The Markdown is generated at request time by:
      1) Rendering the original HTML via ``app.test_client()``.
      2) Converting that HTML to Markdown with ``HtmlToMdGenerator(template_name)``.
      3) Restricting links to the allow-list derived from decorated routes.

    Parameters
    ----------
    app : flask.Flask
        The Flask application instance. A lightweight internal blueprint is
        mounted once per process to serve the ``.html.md`` routes.
    template_dir : str | None, optional
        Filesystem directory to search for the Jinja template used by
        ``HtmlToMdGenerator``. If ``None``, the generator's default loader is used.
    template_name : str
        Jinja template filename used to render the Markdown output. **Required.**
    mount_prefix : str, optional
        URL prefix under which the Markdown mirror is exposed. This becomes the
        blueprint's ``url_prefix`` and is also passed to the generator as
        ``mount_prefix`` for constructing internal links. Defaults to ``""``
        (no prefix).
        Example: ``"/.llms"`` will serve mirrors at ``/.llms/<route>.html.md``.
    blueprint_rule : str, optional
        The blueprint rule that handles Markdown requests. It **must** contain the
        ``<path:raw>`` converter so the target HTML path can be mirrored.
        Defaults to ``"/<path:raw>.html.md"``.
    allow_param_routes : bool, optional
        If ``False`` (default), parameterized routes (containing ``<...>``) are
        **excluded** from the allow-list for safety and predictability. Set to
        ``True`` to mirror concrete requests to dynamic routes you trust.

    Returns
    -------
    Callable[[Callable], Callable]
        A decorator that returns the original view function unchanged, while
        registering it as eligible for Markdown mirroring.

    Raises
    ------
    ValueError
        If ``template_name`` is empty.

    Notes
    -----
    - **Scope/State:** This middleware uses module-level state
      (``_DECORATED_ENDPOINTS``, ``_ENDPOINT_POLICY``, ``_ALLOWED_PATHS``) and mounts
      the internal blueprint once per process. Running multiple Flask apps in the
      same Python process is not supported without additional isolation.
    - **Performance:** Each Markdown request issues an internal HTTP request via
      ``app.test_client()`` to render the original HTML; budget accordingly.
    - **Security:** Only explicitly decorated endpoints are mirrored. If you
      enable ``allow_param_routes=True``, ensure your templates and routes handle
      untrusted parameters safely.
    - **Content Negotiation:** The mirror is served as
      ``text/markdown; charset=utf-8`` and returns 4xx/5xx Markdown bodies on error.

    Examples
    --------
    Basic usage (no prefix)::

        @app.get("/pricing")
        @html2md(app, template_name="html_to_md.jinja")
        def pricing():
            return render_template("pricing.html")
        # -> /pricing (HTML)
        # -> /pricing.html.md (Markdown)

    With a mount prefix (recommended for hiding from users)::

        @app.get("/pricing")
        @html2md(app, template_name="html_to_md.jinja", mount_prefix="/.llms")
        def pricing():
            return render_template("pricing.html")
        # -> /.llms/pricing.html.md (Markdown)
    """
    if not template_name:
        raise ValueError("template_name is required")

    _ensure_html2md_blueprint(
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


def _ensure_llmstxt_blueprint(
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
      3) renders the manifest template *based on that HTML*
    """
    if not template_name:
        raise ValueError("template_name is required")
    if not manifest_path.startswith("/"):
        raise ValueError("manifest_path must start with '/'")

    global _MANIFEST_BP_MOUNTED
    if _MANIFEST_BP_MOUNTED:
        return

    bp = Blueprint("llmstxt_manifest", __name__)

    @bp.get(manifest_path)
    def _llmstxt_manifest():
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
                (
                    f"# {html_resp.status_code}\n"
                    f"Failed to render `{page_path}` for manifest.\n"
                ),
                status=html_resp.status_code,
                mimetype="text/markdown",
            )

        html = html_resp.get_data(as_text=True)
        base = f"{request.scheme}://{request.host}"
        # Use the *source page* as the canonical source_url for the manifest render
        source_url = urljoin(base, page_path)

        # 3) Render your llms.txt template based on that HTML (parser extracts links)
        generator = HtmlToMdGenerator(
            template_dir=template_dir, template_name=template_name
        )
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
    Decorator that keeps the original endpoint as-is (serving HTML) and also
    registers a site manifest route (``manifest_path``, default ``/llms.txt``)
    generated from the decorated page's HTML.

    This is useful for exposing an index or sitemap tailored for LLM crawlers.
    The manifest renderer receives:
      - The HTML of the decorated endpoint (as ``source_url``).
      - The allow-list of all routes decorated with ``@html2md``/**and** respecting
        each endpoint's ``allow_param_routes`` policy.
      - ``mount_prefix`` so links can target your Markdown mirrors (e.g., ``/.llms``).

    Parameters
    ----------
    app : flask.Flask
        The Flask application instance. A dedicated blueprint is mounted once per
        process to serve ``manifest_path``.
    template_dir : str | None, optional
        Filesystem directory to search for the Jinja template used by
        ``HtmlToMdGenerator`` for rendering the manifest.
    template_name : str
        Jinja template filename used to render the manifest. **Required.**
    mount_prefix : str, optional
        A prefix passed to the generator (not the URL of the manifest itself) so
        your template can build links pointing at the Markdown mirrors, e.g.,
        ``/.llms``. Defaults to ``""``.
    manifest_path : str, optional
        Absolute URL rule at which the manifest is exposed. Must start with ``"/"``.
        Defaults to ``"/llms.txt"``.

    Returns
    -------
    Callable[[Callable], Callable]
        A decorator that returns the original view function unchanged, while
        ensuring the manifest route is registered once and rendered from that
        view's HTML.

    Raises
    ------
    ValueError
        If ``template_name`` is empty or ``manifest_path`` does not start with ``"/"``.

    Notes
    -----
    - The manifest uses the **decorated endpoint's HTML** as its canonical source,
      so your Jinja template can discover links (e.g., via parsing) and then
      cross-reference the allow-list to include only mirrored pages.
    - The allow-list is rebuilt from the app's URL map on each manifest request,
      so newly decorated routes appear without restarting.
    - Module-level state is used to mount the manifest blueprint once per process.
    - If multiple rules map to the decorated endpoint, a non-parameterized rule
      is preferred as the canonical ``source_url``.

    Example
    -------
    Basic site index for LLMs::

        @app.get("/")
        @llmstxt(app, template_name="llms.txt.jinja", mount_prefix="/.llms")
        def home():
            return render_template("home.html")

        @app.get("/features")
        @html2md(app, template_name="html_to_md.jinja")
        def features():
            return render_template("features.html")

        # -> / (HTML)
        # -> /llms.txt (manifest rendered from '/' HTML,
        # linking to /.llms/features.html.md, etc.)
    """
    if not template_name:
        raise ValueError("template_name is required")

    def decorator(view_func: Callable) -> Callable:
        # Discover a concrete rule for the decorated HTML endpoint
        # (prefer non-parameterized)
        endpoint = view_func.__name__
        discovered_rule = None
        try:
            for rule in app.url_map.iter_rules():
                if rule.endpoint == endpoint and "<" not in rule.rule:
                    discovered_rule = rule.rule
                    break
        except Exception:
            discovered_rule = None

        _ensure_llmstxt_blueprint(
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
