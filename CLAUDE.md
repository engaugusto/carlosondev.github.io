# AGENTS.md

Guidance for AI coding agents (Claude Code, Codex, etc.) working in this repo.

## Project

Hugo + Hextra blog for carlosondev.com in three languages: `en` (default), `es` (es-ES), `pt-br` (pt-BR).
All tooling runs through **mise** (`mise.toml`). Never call Ruby, Docker or a global Hugo — use `mise run <task>`.

## Rules

- Posts: `content/YYYY/MM/DD/<slug>/index.<lang>.md`, one file per language. Create with `mise run new "Title"`.
- Every published post needs `title`, `date`, `description` (one-sentence TL;DR) and `tags`.
- Tags come only from `data/tag_taxonomy.yml`, using the name for the file's language. Search first:
  `mise run tags:search "..."`. All translations of a post must map to the same canonical tags.
- Do not edit `content/_index.*.md` or `content/archives/_index.*.md` by hand — run `mise run index`.
- Never commit `_index` files generated with `--drafts`/`--future`.
- Spanish is from Spain (es-ES); Portuguese is Brazilian (pt-BR).
- Do not edit `_vendor/` by hand; update the theme with `mise run theme:update`.
- Override Hextra templates by copying them into `layouts/` with the same path.

## Before you finish

```bash
mise run check    # tags, stale-index check, tests, build
```
