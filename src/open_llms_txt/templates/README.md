# Templates

This folder contains the **Jinja2/Nunjucks templates** used to render Markdown (`.md`) and `llms.txt` files from parsed HTML input.
It provides a **portable template layer** that can be reused in Python (Jinja2) and Node.js (Nunjucks).

---

## Structure

```
templates/
├── html_to_md.jinja      # Main template to render Markdown
├── llms.txt.jinja        # Template to render llms.txt
└── partials/
    ├── links.jinja       # Engine-specific Links block (Jinja2, Pythonic style)
    └── links.njk         # Engine-specific Links block (Nunjucks, Node-friendly)
```

---

## Template Flow

1. **`html_to_md.jinja`**

   * The entry point for Markdown generation.
   * Renders metadata, title, paragraphs, headings, and links.
   * Decides which *Links* partial to include based on the `engine` variable.

   ```jinja
   {% if engine == "jinja2" %}
     {% include "partials/links.jinja" %}
   {% else %}
     {% include "partials/links.njk" %}
   {% endif %}
   ```

2. **`partials/links.jinja`** (Python Jinja2)

   * Uses Python string methods (`.startswith`, `.endswith`, `.rstrip`) to normalize links.
   * Safe to use in Jinja2 but not in Nunjucks.

3. **`partials/links.njk`** (Node Nunjucks)

   * Equivalent logic, but written with slicing and conditionals instead of Python methods.
   * Ensures portability to JavaScript runtimes.

4. **`llms.txt.jinja`**

   * Generates `llms.txt` files with crawl policy, root URL, and license information.
   * Similar structure, but tailored to the LLMs crawler convention.

---

## Features

* **Portable Engine Support**
  By switching the `engine` parameter in your render call, the template chooses the correct partial (`jinja` or `njk`).

* **Metadata Section**
  Standardized header block with:

  * `Root`: canonical root URL
  * `Source`: source page
  * `License`: default `CC-BY-4.0`
  * `Crawl Policy`: default `allow`

* **Dynamic Content**

  * Title: from `<h1>` or `<title>`
  * Paragraphs: collected `<p>` tags
  * Headings: collected `<h2>`/`<h3>` tags
  * Links: normalized relative/absolute paths, `.html → .md` conversion

* **Whitespace-Friendly**
  Templates use `trim_blocks` and `lstrip_blocks` to minimize blank lines.

---

## Usage

In Python (Jinja2):

```python
from open_llms_txt.generator.html_to_md import HtmlToMdGenerator, TemplateEngine

gen = HtmlToMdGenerator()
html = open("examples/site/index.html").read()

md = gen.render(
    html,
    root_url="https://example.com",
    source_url="https://example.com/index.html",
    engine=TemplateEngine.JINJA2
)

print(md)
```

In Node (Nunjucks):

```js
import nunjucks from "nunjucks";

const env = nunjucks.configure("src/open_llms_txt/templates", {
  autoescape: false,
  trimBlocks: true,
  lstripBlocks: true,
});

const html = fs.readFileSync("examples/site/index.html", "utf8");
const context = parseHtmlToJson(html, "https://example.com", "https://example.com/index.html");

const md = env.render("html_to_md.jinja", {
  ...context,
  engine: "nunjucks"
});

console.log(md);
```

---

## Extending

* To change how links are rendered, edit the engine-specific partial (`links.jinja` or `links.njk`).
* To add more sections (e.g., `<h4>`, lists, tables), update `html_to_md.jinja` or create new partials.
* You can add more partials under `partials/` and include them conditionally.

---

With this structure, your templates are **engine-portable, easy to extend, and cleanly separated** between presentation and scraping logic.

