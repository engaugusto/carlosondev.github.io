#!/usr/bin/env python3
"""Search, document and validate the controlled tag taxonomy.

Python port of akitaonrails.github.io's scripts/tag_catalog.rb, for any number
of languages. Canonical tags live in data/tag_taxonomy.yml; each one has a
localized name per language, a description and optional aliases.

Usage:
  mise run tags:search "title and central subjects"
  mise run tags:check            # validate every published post (CI runs this)
  mise run tags:catalog          # rewrite TAGGING.md

--check fails when a published post:
  * has no tags or no description,
  * uses a tag that is not in the taxonomy for its language,
  * has translations whose tags don't map to the same canonical tags.
"""

from __future__ import annotations

import argparse
import difflib
import sys
from collections import defaultdict

from blog import ROOT, all_posts, languages, normalize, tag_map, taxonomy


def entries() -> list[dict]:
    return [
        {
            "id": tag_id,
            "names": {lang: values.get(lang, "") for lang in languages()},
            "description": values.get("description", ""),
            "kind": values.get("kind", "topic"),
            "aliases": [str(a) for a in values.get("aliases", [])],
        }
        for tag_id, values in taxonomy()["tags"].items()
    ]


# --------------------------------------------------------------------------- search

def search(query: str) -> list[str]:
    q = normalize(query)
    tokens = [t for t in q.split() if len(t) >= 3]
    scored = []
    for entry in entries():
        fields = [normalize(v) for v in (entry["id"], *entry["names"].values(), entry["description"], *entry["aliases"])]
        exact = q in fields
        phrase = any(q in f for f in fields)
        hits = sum(1 for t in tokens if any(t in f for f in fields))
        score = (100 if exact else 0) + (40 if phrase else 0) + hits
        if score:
            scored.append((score, entry))
    scored.sort(key=lambda item: (-item[0], item[1]["id"]))
    lines = []
    for _, entry in scored[:15]:
        names = " | ".join(f"{lang}: {name}" for lang, name in entry["names"].items())
        aliases = f" | aliases: {', '.join(entry['aliases'])}" if entry["aliases"] else ""
        lines.append(f"{names} — {entry['description']}{aliases}")
    return lines


# --------------------------------------------------------------------------- catalog

def md(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_catalog() -> str:
    langs = languages()
    header = "| " + " | ".join(langs) + " | Purpose | Aliases |"
    rule = "|" + "---|" * (len(langs) + 2)
    groups = defaultdict(list)
    for entry in entries():
        groups["Projects and series" if entry["kind"] in ("project", "series") else "Topics"].append(entry)

    lines = [
        "# Tag catalog",
        "",
        "Generated from `data/tag_taxonomy.yml` by `mise run tags:catalog`. Do not edit by hand.",
        "",
        "Before tagging a post, search the catalog:",
        "",
        "```bash",
        'mise run tags:search "post title and central subjects"',
        "```",
        "",
        "Reuse existing tags. Add a new one to the YAML only for a recurring subject that no",
        "existing tag covers — never a spelling, plural or language variant of an existing tag.",
        "Every tag needs a name in each language.",
        "",
    ]
    for title in ("Projects and series", "Topics"):
        items = sorted(groups.get(title, []), key=lambda e: e["id"])
        if not items:
            continue
        lines += [f"## {title} ({len(items)})", "", header, rule]
        for e in items:
            names = " | ".join(f"`{md(e['names'][lang])}`" for lang in langs)
            lines.append(f"| {names} | {md(e['description'])} | {md(', '.join(e['aliases']) or '-')} |")
        lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- check

def check() -> bool:
    failures: list[str] = []
    langs = languages()

    for entry in entries():
        missing = [lang for lang in langs if not entry["names"].get(lang)]
        if missing:
            failures.append(f"data/tag_taxonomy.yml: tag `{entry['id']}` has no name for {', '.join(missing)}")

    maps = {lang: tag_map(lang) for lang in langs}
    published = [post for post in all_posts() if post.published()]
    by_bundle = defaultdict(dict)

    for post in published:
        rel = post.path.relative_to(ROOT)
        if not post.tags:
            failures.append(f"{rel}: no tags")
        if not post.description:
            failures.append(f"{rel}: no description (it is the TL;DR shown on the home page)")
        for tag in post.tags:
            if tag not in maps[post.lang]:
                close = difflib.get_close_matches(tag, maps[post.lang].keys(), n=3)
                hint = f"; did you mean {', '.join(f'`{c}`' for c in close)}?" if close else ""
                failures.append(f"{rel}: unknown {post.lang} tag `{tag}`{hint}")
        by_bundle[post.bundle][post.lang] = post

    for bundle, posts in by_bundle.items():
        if len(posts) < 2:
            continue
        ids = {lang: sorted(maps[lang].get(t, f"?{t}") for t in post.tags) for lang, post in posts.items()}
        if len({tuple(v) for v in ids.values()}) > 1:
            detail = "; ".join(f"{lang}: {', '.join(v)}" for lang, v in ids.items())
            failures.append(f"{bundle.relative_to(ROOT)}: translations use different tags ({detail})")

    if failures:
        print("\n".join(failures), file=sys.stderr)
        return False
    print(f"Tag catalog check passed for {len(published)} published files.")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--search", metavar="QUERY", help="find canonical tags by name, alias or meaning")
    parser.add_argument("--check", action="store_true", help="validate tags of all published posts")
    parser.add_argument("--write", metavar="PATH", help="write the Markdown catalog to PATH")
    args = parser.parse_args()

    ok = check() if args.check else True
    if args.search:
        results = search(args.search)
        print("\n".join(results) if results else "No matching canonical tags.")
    elif args.write:
        (ROOT / args.write).write_text(render_catalog() + "\n", encoding="utf-8")
        print(f"Wrote {args.write}")
    elif not args.check:
        print(render_catalog())
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
