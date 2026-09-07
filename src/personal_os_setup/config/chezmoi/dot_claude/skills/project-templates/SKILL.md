---
name: project-templates
description: Use when starting to build a NEW app, package, or project from scratch — pick the right forkable template instead of an empty repo. Lists the user's three templates and their CI/CD + docs setup.
---

# Starting a new project — pick a template

Never start from an empty repo. Fork the template matching the project type — all three already
ship CI/CD, GitHub Pages docs site, pre-commit, and release tooling, so you replace content, not plumbing.

| Build target | Fork | Stack / notes |
|---|---|---|
| Python package / library | [python-package-template](https://github.com/AmineDjeghri/python-package-template) | uv-based package, tests, pre-commit, semantic-release |
| Generative-AI project, or full-stack (backend + frontend) | [generative-ai-project-template](https://github.com/AmineDjeghri/generative-ai-project-template) | FastAPI + NiceGUI; litellm/ollama (cloud + local LLMs); langfuse observability |
| Home Assistant addon | [ha-addons](https://github.com/AmineDjeghri/ha-addons) (octo-fiesta pattern: per-addon `config.yaml`/`Dockerfile`/`run.sh`, HA Store release flow) — or fork it as the base for your own addon collection |

Rules:
1. **Match the type first** (package vs gen-ai/full-stack vs addon) — don't retrofit a template.
2. **Fork, don't clone** — keep the upstream link so template improvements can be pulled in later.
3. **After forking, make the repo self-describing**: add `AGENTS.md`/`CLAUDE.md` + `.claude/skills/` (see `repo-conventions`) so any agent works in it correctly from day one.
4. Rebrand/rename the package per the template's own README before first use.
