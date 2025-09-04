# Contributing

Thanks for your interest in **open-llms-txt**! This project is an MVP/architecture proposal for exposing **LLM-friendly** views (.html.md) and a lightweight llms.txt manifest. We welcome issues, ideas, and PRs.

We believe **llms.txt** can become a key enabler for **LLM-friendly web standards**. Contributions of all sizes—bugfixes, docs, new ideas—help us shape this ecosystem.

This repo follows **standard open-source practices**. If transferred to an organization (e.g. IBM OSS), contributor guidelines will remain consistent.

## In General
- If you have an itch, feel free to scratch it.
- Start by opening an issue to discuss larger changes or new features.
- Small fixes and docs improvements are welcome directly as PRs.

## How we work (PRs & commits)

We use small feature branches + **squash & merge** into **main**.
- **Branch from main**: feat/my-thing, fix/parser-edge, refactor/middleware, docs/readme, style/ruff-fixes.
- **Commit message prefixes [Conventional Commits subset](https://www.conventionalcommits.org/en/v1.0.0/)**:
  - `feat`: …, `fix`: …, `refactor`: …, `style`: …, `docs`: …
- **PR titles** should use the same prefixes, since we squash-merge.
- **Reference issues in the PR body**: Fixes #123 or Refs #456.

### PR checklist (please confirm before requesting review)
- `mise run style` (ruff fix + format)
- `mise run check` (lint w/o changes, format check, mypy)
- `mise run tests` (pytest)
- Updated/added tests for new behavior
- DCO sign-off on commits (`git commit -s`)

## Getting started (dev environment)

This repo uses mise for tasks/tooling and uv for dependency management & builds.

```bash
# 1) Install mise (if not already)
curl https://mise.run | sh
~/.local/bin/mise --version
# mise 2024.x.x
# shell hook (zsh example):  eval "$(mise activate zsh)"

# 2) Install tools from [tools] (Python, uv)
mise install

# 3) Create/refresh the venv and install main+dev deps
mise run setup   # runs: uv sync --dev and installs git hooks

# 4) See available tasks
mise run
```

### Common tasks (defined in mise.toml)

```bash
mise run style        # ruff check --fix + ruff format
mise run check        # lint (no fix), format --check, mypy
mise run tests        # pytest
mise run build        # uv build (wheel + sdist)
```

The **git hooks** installed by mise run setup run:
- pre-commit → mise run check
- pre-push → mise run tests

(They’re just tiny scripts in .git/hooks, so CI and local are aligned.)

## Proposing new features

Please open an **issue** first to discuss scope and approach. That avoids rework and helps us align on the architecture. Include:
- Problem & motivation
- Proposed API/UX
- Backwards compatibility considerations
- Test plan

## Fixing bugs

Open an issue describing the bug and steps to reproduce. In your PR:
- Add/adjust tests that fail without your fix.
- Keep the fix minimal and targeted.

## Testing

We use **pytest** (with `pytest-asyncio`) and keep tests under `tests/`.
- Async tests are supported (`asyncio_mode = "auto"``).
- Network **is blocked by default** via `tests/conftest.py`. If a test truly needs the network, mark it with `@pytest.mark.network`.

Useful invocations:

```bash
mise run tests
uv run pytest -q
uv run pytest -k web_scraper
```

Run the example app locally with flask (optional):

```bash
uv run python examples/flask_site/complex_app.py
curl -s http://127.0.0.1:8000/pricing.html.md | sed -n '1,20p'
curl -s http://127.0.0.1:8000/llms.txt | sed -n '1,20p'
```

## Coding style guidelines
- **Formatting & linting**: handled by **Ruff**
  - `mise run style` applies both lint *fixes* and *formatting*.
  - Import order, unused imports, naming, etc., are enforced by Ruff.
- **Typing**: use Python type hints; we run **mypy** (mise `run typecheck`).
- **Naming**: PEP 8 (modules `lower_snake_case`, classes `CapWords`).
  - Packages that hold multiple implementations use **plural** (`parsers/`, `scrapers/`).
- **Long lines**: wrap with implicit concatenation for strings, e.g.:
```py
html = (
    "<html><head><title>Pricing</title></head><body>"
    "<h1>Our Pricing</h1>"
    "</body></html>"
)
```

- **Docs**: update README/examples when you add notable behavior.

## Merge approval

At least **one maintainer** is required before squash-merge to main. Larger or risky changes may require two reviewers.

## Legal

This project is licensed under **Apache License 2.0**.
- Add SPDX headers to new source files:
```py
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024–2025
```

- We use the **Developer Certificate of Origin (DCO)**. Sign off your commits:
```bash
git commit -s -m "feat: add fastapi adapter"
```
This adds:
```bash
Signed-off-by: Your Name <you@example.com>
```

## Communication
- Open an **issue** for bugs/feature requests.
- Use **PR discussions** for implementation details.
- (If a Slack/Discord/Discussions channel is added later, we’ll link it here.)

## CI / Local CI
- GitHub Actions workflow runs `mise run check` and `mise run tests`.
- You can simulate CI locally with **act** (Docker required):

```bash
act push -j checks-tests
```

---

Thanks again for contributing! If you’re unsure about anything, open an issue and we’ll help you get started.