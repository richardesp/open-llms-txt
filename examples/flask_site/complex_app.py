from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response
from jinja2 import DictLoader
from datetime import datetime
import re

# Keep your decorator (uses template_name="html_to_md.jinja" which we inject into the Jinja loader)
from open_llms_txt.middleware.flask import html2md, llmstxt

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret-change-me"

# -----------------------------
# In-memory templates + CSS
# -----------------------------
TEMPLATES = {
    # ---- Base layout shared by all pages ----
    "base.html": r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>{% block title %}Acme – Demo{% endblock %}</title>
  <link rel="stylesheet" href="{{ url_for('styles_css') }}">
  <link rel="icon" href="{{ url_for('logo_svg') }}">
  <meta name="description" content="All-in-one Flask single-file demo with CSS, tables, images, and forms."/>
</head>
<body>
  <nav class="nav">
    <a class="brand" href="{{ url_for('home') }}">
      <img class="logo" alt="Acme" src="{{ url_for('logo_svg') }}" width="24" height="24"/> Acme
    </a>
    <div class="nav-links">
      <a href="{{ url_for('pricing') }}">Pricing</a>
      <a href="{{ url_for('features') }}">Features</a>
      <a href="{{ url_for('gallery') }}">Gallery</a>
      <a href="{{ url_for('about') }}">About</a>
      <a href="{{ url_for('contact_get') }}">Contact</a>
    </div>
  </nav>

  <main class="container">
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        <div class="flash-stack">
          {% for category, msg in messages %}
            <div class="flash {{ category }}">{{ msg }}</div>
          {% endfor %}
        </div>
      {% endif %}
    {% endwith %}
    {% block content %}{% endblock %}
  </main>

  <footer class="footer">
    <div class="grid">
      <div>
        <h4>Product</h4>
        <ul>
          <li><a href="{{ url_for('pricing') }}">Pricing</a></li>
          <li><a href="{{ url_for('features') }}">Features</a></li>
          <li><a href="{{ url_for('gallery') }}">Gallery</a></li>
        </ul>
      </div>
      <div>
        <h4>Company</h4>
        <ul>
          <li><a href="{{ url_for('about') }}">About</a></li>
          <li><a href="{{ url_for('contact_get') }}">Contact</a></li>
        </ul>
      </div>
      <div>
        <h4>API</h4>
        <ul>
          <li><a href="{{ url_for('api_health') }}">/api/health</a></li>
          <li><a href="{{ url_for('api_time') }}">/api/time</a></li>
        </ul>
      </div>
    </div>
    <p class="muted">© {{ current_year }} Acme Demo</p>
  </footer>

  <script>
    // Tiny accordion for FAQs
    document.addEventListener('click', (e) => {
      if (e.target.matches('.faq-question')) {
        const ans = e.target.nextElementSibling;
        ans.classList.toggle('open');
      }
    });
  </script>
</body>
</html>
""",

    # ---- Home page ----
    "home.html": r"""
{% extends "base.html" %}
{% block title %}Acme – Build faster{% endblock %}
{% block content %}
<section class="hero">
  <h1>Build and ship delightful experiences</h1>
  <p class="lead">
    Single-file Flask demo with a clean design, multiple routes, tables, images & forms.
  </p>
  <div class="cta-row">
    <a class="btn btn-primary" href="{{ url_for('pricing') }}">See Pricing</a>
    <a class="btn btn-secondary" href="{{ url_for('features') }}">Explore Features</a>
  </div>
</section>

<section class="features grid">
  <div class="card">
    <h3>Speed</h3>
    <p>Opinionated defaults to get you to “Hello, world!” in no time.</p>
  </div>
  <div class="card">
    <h3>Reliability</h3>
    <p>Graceful error pages and simple validations included.</p>
  </div>
  <div class="card">
    <h3>Flexibility</h3>
    <p>Custom decorator for HTML → Markdown view on the pricing page.</p>
  </div>
</section>
{% endblock %}
""",

    # ---- Features page (table + small comparison) ----
    "features.html": r"""
{% extends "base.html" %}
{% block title %}Features – Acme{% endblock %}
{% block content %}
<section class="prose">
  <h1>Features</h1>
  <p>Here’s a quick comparison of what you get out of the box.</p>
</section>

<div class="table-wrap">
  <table class="compare">
    <thead>
      <tr>
        <th>Feature</th><th>Free</th><th>Pro</th><th>Team</th>
      </tr>
    </thead>
    <tbody>
      <tr><td>Projects</td><td>3</td><td>Unlimited</td><td>Unlimited</td></tr>
      <tr><td>Seats</td><td>1</td><td>1</td><td>10</td></tr>
      <tr><td>SSO</td><td>—</td><td>Basic SSO</td><td>SAML SSO</td></tr>
      <tr><td>Support</td><td>Community</td><td>Priority</td><td>Priority + Slack</td></tr>
      <tr><td>Workspaces</td><td>—</td><td>—</td><td>Shared</td></tr>
    </tbody>
  </table>
</div>

<section class="faq">
  <h2>FAQ</h2>
  <button class="faq-question">Can I cancel anytime?</button>
  <div class="faq-answer"><p>Yes, you can cancel at any time.</p></div>
  <button class="faq-question">Do you offer discounts?</button>
  <div class="faq-answer"><p>Yes, annual plans include a discount.</p></div>
</section>
{% endblock %}
""",

    # ---- Gallery page (images) ----
    "gallery.html": r"""
{% extends "base.html" %}
{% block title %}Gallery – Acme{% endblock %}
{% block content %}
<section class="prose">
  <h1>Gallery</h1>
  <p>Some great royalty-free placeholders from <code>picsum.photos</code>.</p>
</section>

<div class="gallery-grid">
  <figure class="card">
    <img src="https://picsum.photos/seed/kit/720/420" alt="Random 1" loading="lazy"/>
    <figcaption>Random Photo #1</figcaption>
  </figure>
  <figure class="card">
    <img src="https://picsum.photos/seed/fox/720/420" alt="Random 2" loading="lazy"/>
    <figcaption>Random Photo #2</figcaption>
  </figure>
  <figure class="card">
    <img src="https://picsum.photos/seed/sea/720/420" alt="Random 3" loading="lazy"/>
    <figcaption>Random Photo #3</figcaption>
  </figure>
</div>
{% endblock %}
""",

    # ---- About page ----
    "about.html": r"""
{% extends "base.html" %}
{% block title %}About – Acme{% endblock %}
{% block content %}
<section class="prose">
  <h1>About Acme</h1>
  <p>We build simple, reliable tools for developers and teams.</p>
  <p>This page, like the entire site, lives in a single Python file.</p>
</section>
{% endblock %}
""",

    # ---- Contact page ----
    "contact.html": r"""
{% extends "base.html" %}
{% block title %}Contact – Acme{% endblock %}
{% block content %}
<section class="prose">
  <h1>Contact us</h1>
  <p>Questions or feedback? We’d love to hear from you.</p>
</section>

<form action="{{ url_for('contact_post') }}" method="POST" class="stack">
  <label>Name
    <input type="text" name="name" required>
  </label>
  <label>Email
    <input type="email" name="email" required>
  </label>
  <label>Message
    <textarea name="message" rows="6" placeholder="How can we help?" required></textarea>
  </label>
  <button class="btn btn-primary" type="submit">Send</button>
</form>
{% endblock %}
""",

    # ---- Thank you page ----
    "thank_you.html": r"""
{% extends "base.html" %}
{% block title %}Thanks – Acme{% endblock %}
{% block content %}
<section class="prose center">
  <h1>Thanks, {{ name }}!</h1>
  <p>We’ll get back to you soon.</p>
  <p><a class="btn" href="{{ url_for('home') }}">Return home</a></p>
</section>
{% endblock %}
""",

    # ---- Error pages ----
    "404.html": r"""
{% extends "base.html" %}
{% block title %}Not Found – Acme{% endblock %}
{% block content %}
<section class="prose center">
  <h1>404</h1>
  <p>The page you’re looking for doesn’t exist.</p>
  <a class="btn" href="{{ url_for('home') }}">Go home</a>
</section>
{% endblock %}
""",
    "500.html": r"""
{% extends "base.html" %}
{% block title %}Server Error – Acme{% endblock %}
{% block content %}
<section class="prose center">
  <h1>Something went wrong</h1>
  <p>Please try again later.</p>
  <a class="btn" href="{{ url_for('home') }}">Go home</a>
</section>
{% endblock %}
""",

    "pricing.html": r"""
{% extends "base.html" %}
{% block title %}Pricing – Acme{% endblock %}
{% block content %}

<section class="pricing-hero">
  <h1>Pricing Plans</h1>
  <p>Simple, transparent plans for teams of any size. Annual billing saves <strong>20%</strong>.</p>
</section>

<section class="pricing-grid">
  <article class="pricing-card">
    <h2>Free</h2>
    <p class="price">$0 <span>/mo</span></p>
    <ul>
      <li>3 projects</li>
      <li>Community support</li>
      <li>Basic analytics</li>
    </ul>
    <form action="{{ url_for('signup') }}" method="POST">
      <input type="hidden" name="plan" value="free">
      <input type="email" name="email" placeholder="you@company.com" required>
      <button type="submit">Get Started</button>
    </form>
  </article>

  <article class="pricing-card highlight">
    <h2>Pro <span class="tag">Most Popular</span></h2>
    <p class="price">$29 <span>/mo</span></p>
    <ul>
      <li>Unlimited projects</li>
      <li>SSO</li>
      <li>Priority email support</li>
      <li>Audit logs</li>
    </ul>
    <form action="{{ url_for('signup') }}" method="POST">
      <input type="hidden" name="plan" value="pro">
      <input type="email" name="email" placeholder="you@company.com" required>
      <button type="submit">Start Pro</button>
    </form>
  </article>

  <article class="pricing-card">
    <h2>Team</h2>
    <p class="price">$99 <span>/mo</span></p>
    <ul>
      <li>10 seats included</li>
      <li>SAML SSO</li>
      <li>Shared workspaces</li>
      <li>Role-based access control</li>
    </ul>
    <form action="{{ url_for('signup') }}" method="POST">
      <input type="hidden" name="plan" value="team">
      <input type="email" name="email" placeholder="you@company.com" required>
      <button type="submit">Start Team</button>
    </form>
  </article>
</section>

<section class="addons">
  <h2>Add-ons</h2>
  <table>
    <tr><th>Add-on</th><th>Price</th><th>Notes</th></tr>
    <tr><td>Extra seats</td><td>$5/seat</td><td>Beyond 10 included seats</td></tr>
    <tr><td>Premium SLA</td><td>$49/mo</td><td>1-hour response time</td></tr>
    <tr><td>Dedicated onboarding</td><td>$299 one-time</td><td>Migration support</td></tr>
  </table>
</section>

<section class="faq">
  <h2>FAQ</h2>
  <details><summary>Can I cancel anytime?</summary><p>Yes, no long-term contracts.</p></details>
  <details><summary>Do you offer discounts?</summary><p>Annual billing saves 20%. Non-profit discounts available.</p></details>
  <details><summary>Is there a free trial?</summary><p>Yes, 7-day trial for Pro and Team plans.</p></details>
</section>

<section class="testimonials">
  <h2>What our customers say</h2>
  <blockquote>
    “Switched to Pro and shipped in half the time. Worth every dollar.”
    <br><cite>— Taylor, Indie Dev</cite>
  </blockquote>
</section>

{% endblock %}
"""
}

CSS = r"""
:root {
  --bg: #0b1020;
  --panel: #111833;
  --text: #e7eaf6;
  --muted: #a9b0c7;
  --primary: #6aa0ff;
  --primary-contrast: #071124;
  --border: #1f2a4a;
  --success: #2ecc71;
  --error: #ff6b6b;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:var(--bg);color:var(--text);font:16px/1.6 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
a{color:var(--primary);text-decoration:none}
a:hover{text-decoration:underline}
.container{max-width:1050px;margin:0 auto;padding:24px}

/* Nav */
.nav{display:flex;align-items:center;justify-content:space-between;padding:16px 24px;border-bottom:1px solid var(--border);background:rgba(17,24,51,.6);backdrop-filter:blur(6px);position:sticky;top:0;z-index:5}
.brand{font-weight:800;font-size:20px;letter-spacing:.5px;display:flex;align-items:center;gap:8px}
.logo{vertical-align:middle;filter:drop-shadow(0 0 2px rgba(0,0,0,.2))}
.nav-links a{margin-left:18px}

/* Footer */
.footer{border-top:1px solid var(--border);padding:32px 24px;margin-top:56px}
.footer .grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.footer h4{margin:0 0 8px}
.footer ul{list-style:none;padding:0;margin:0}
.footer li{margin:6px 0}
.muted{color:var(--muted)}

/* Hero */
.hero{text-align:center;padding:64px 0}
.hero h1{font-size:44px;margin-bottom:12px}
.lead{color:var(--muted);font-size:18px}

/* Buttons */
.btn{display:inline-block;border:1px solid var(--border);background:var(--panel);color:var(--text);padding:10px 14px;border-radius:10px;cursor:pointer}
.btn:hover{filter:brightness(1.05)}
.btn-primary{background:var(--primary);color:var(--primary-contrast);border-color:transparent;font-weight:700}
.btn-secondary{background:#233056}
.btn-link{background:transparent;border:none;padding:0;color:var(--primary)}

/* Layout helpers */
.grid{display:grid;gap:16px;grid-template-columns:repeat(3,1fr)}
.center{text-align:center}
.stack{display:grid;gap:12px;max-width:560px}

/* Cards */
.card{background:var(--panel);border:1px solid var(--border);padding:18px;border-radius:14px}

/* Tables */
.table-wrap{overflow-x:auto}
.compare{width:100%;border-collapse:collapse;margin-top:12px}
.compare th,.compare td{border:1px solid var(--border);padding:10px}
.compare th{background:#0e1430}

/* Prose */
.prose h1,.prose h2,.prose h3{margin-top:0}
.prose p{color:var(--text)}

/* Flash */
.flash-stack{display:grid;gap:8px;margin:16px 0}
.flash{padding:10px 12px;border-radius:8px}
.flash.info{background:#17324d;border:1px solid #244a70}
.flash.success{background:#173d2a;border:1px solid #245a3c}
.flash.error{background:#4a1b1b;border:1px solid #6b2a2a}

/* Gallery */
.gallery-grid{display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(260px,1fr))}
.gallery-grid img{width:100%;height:auto;border-radius:10px;display:block}

/* FAQ */
.faq-question{width:100%;text-align:left;padding:12px;border:1px solid var(--border);background:var(--panel);border-radius:10px;margin:8px 0 0;cursor:pointer}
.faq-answer{display:none;border:1px solid var(--border);border-top:none;padding:12px;background:#0e1430;border-radius:0 0 10px 10px}
.faq-answer.open{display:block}

/* --- Pricing --- */
.pricing-hero { text-align: center; margin: 40px 0; }
.pricing-hero h1 { font-size: 42px; margin-bottom: 12px; }
.pricing-hero p { color: var(--muted); font-size: 18px; }

.pricing-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 20px;
  margin: 30px 0;
}

.pricing-card {
  background: var(--panel);
  border: 1px solid var(--border);
  padding: 20px;
  border-radius: 14px;
  display: flex;
  flex-direction: column;
  align-items: stretch;
}
.pricing-card h2 { margin-top: 0; }
.pricing-card .price {
  font-size: 32px;
  margin: 8px 0;
}
.pricing-card .price span { color: var(--muted); font-size: 14px; }
.pricing-card ul { list-style: none; padding: 0; margin: 0 0 14px; }
.pricing-card li { padding-left: 18px; position: relative; margin: 6px 0; }
.pricing-card li::before { content: "✓"; position: absolute; left: 0; color: var(--success); }

.pricing-card form { display: grid; gap: 8px; }
.pricing-card input { width: 100%; }
.pricing-card button {
  background: var(--primary);
  color: var(--primary-contrast);
  font-weight: 600;
  border: none;
  padding: 10px;
  border-radius: 8px;
  cursor: pointer;
}
.pricing-card button:hover { filter: brightness(1.1); }

.pricing-card.highlight {
  border: 2px solid var(--primary);
  transform: scale(1.02);
}

.pricing-card .tag {
  background: var(--primary);
  color: var(--primary-contrast);
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 6px;
  margin-left: 8px;
}

.addons { margin: 40px 0; }
.addons table { width: 100%; border-collapse: collapse; }
.addons th, .addons td { border: 1px solid var(--border); padding: 10px; }
.addons th { background: #0e1430; }

.testimonials { margin: 40px 0; text-align: center; }
.testimonials blockquote {
  font-size: 18px;
  font-style: italic;
  margin: 0 auto;
  max-width: 600px;
  color: var(--muted);
}
.testimonials cite { display: block; margin-top: 8px; font-style: normal; color: var(--text); }
"""

# Inject templates into Flask's loader
app.jinja_loader = DictLoader(TEMPLATES)


# -----------------------------
# Utilities
# -----------------------------
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def valid_email(s: str) -> bool:
    return bool(s and EMAIL_RE.match(s))


# -----------------------------
# Asset + CSS endpoints (single-file friendly)
# -----------------------------
@app.get("/static/styles.css")
def styles_css():
    return Response(CSS, mimetype="text/css")

@app.get("/assets/logo.svg")
def logo_svg():
    svg = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#6aa0ff"/>
      <stop offset="1" stop-color="#7cf"/>
    </linearGradient>
  </defs>
  <rect width="64" height="64" rx="12" fill="url(#g)"/>
  <path d="M18 40 L32 16 L46 40 Z" fill="#071124"/>
  <circle cx="32" cy="40" r="6" fill="#071124"/>
</svg>
""".strip()
    return Response(svg, mimetype="image/svg+xml")


# -----------------------------
# HTML pages
# -----------------------------
@app.context_processor
def inject_globals():
    return {"current_year": datetime.utcnow().year}

@app.get("/")
@llmstxt(app, template_name="llms.txt.jinja")
def home():
    return render_template("home.html")

@app.get("/about")
@html2md(app, template_name="html_to_md.jinja")
def about():
    return render_template("about.html")

@app.get("/features")
@html2md(app, template_name="html_to_md.jinja")
def features():
    return render_template("features.html")

@app.get("/gallery")
@html2md(app, template_name="html_to_md.jinja")
def gallery():
    return render_template("gallery.html")

# ---- Pricing page rendered through your decorator (HTML → Markdown) ----
@app.get("/pricing")
@html2md(app, template_name="html_to_md.jinja")
def pricing():
    return render_template("pricing.html")


# ---- Contact (GET/POST) ----
@app.get("/contact")
def contact_get():
    return render_template("contact.html")

@app.post("/contact")
def contact_post():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    message = request.form.get("message", "").strip()

    errors = []
    if not name:
        errors.append("Please enter your name.")
    if not valid_email(email):
        errors.append("Please enter a valid email address.")
    if len(message) < 20:
        errors.append("Your message should be at least 20 characters.")

    if errors:
        for e in errors:
            flash(e, "error")
        return redirect(url_for("contact_get"))

    flash("Thanks! We received your message.", "success")
    return render_template("thank_you.html", name=name)

# ---- Signup (from pricing form) ----
@app.post("/signup")
def signup():
    email = request.form.get("email", "")
    plan = request.form.get("plan", "free")
    if not valid_email(email):
        flash("Please provide a valid email address.", "error")
        return redirect(url_for("pricing"))
    flash(f"Thanks for signing up for the {plan.title()} plan!", "success")
    return redirect(url_for("home"))

# ---- Tiny API ----
@app.get("/api/health")
def api_health():
    return jsonify(status="ok", service="acme-demo", time=datetime.utcnow().isoformat() + "Z")

@app.get("/api/time")
def api_time():
    now = datetime.utcnow()
    return jsonify(utc=now.isoformat() + "Z", epoch=int(now.timestamp()))

# ---- Error demo + handlers ----
@app.get("/error-demo")
def error_demo():
    # Intentionally raise to show the 500 page
    raise RuntimeError("Demonstration error")

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500


if __name__ == "__main__":
    # Bind a friendly host/port; debug True for quick iteration
    app.run(port=8000, debug=True)
