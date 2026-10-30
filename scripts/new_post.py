#!/usr/bin/env python3
"""Create a new post bundle with one draft file per language.

Replaces the `new-post` command of akitaonrails.github.io's scripts/dev.sh.

  mise run new "My post title"
  mise run new "My post title" --slug my-post --lang en,pt-br --date 2026-11-02

Creates content/YYYY/MM/DD/<slug>/index.<lang>.md for each language, as drafts.
Translate the title, add a translated `slug:` if you want a localized URL, write a
one-sentence `description:` (TL;DR shown on the home page), pick tags with
`mise run tags:search`, then set `draft: false` and run `mise run index`.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys

from blog import CONTENT_DIR, ROOT, languages, slugify

TEMPLATE = """---
title: "{title}"
date: "{date}"
slug: {slug}
description: ""
tags: []
featured: false
draft: true
---

"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("title", nargs="+", help="post title (in your writing language)")
    parser.add_argument("--slug", help="directory/URL slug (default: from the title)")
    parser.add_argument("--lang", default=",".join(languages()),
                        help=f"comma-separated languages (default: {','.join(languages())})")
    parser.add_argument("--date", help="YYYY-MM-DD or full ISO timestamp (default: now)")
    args = parser.parse_args()

    title = " ".join(args.title).strip()
    slug = args.slug or slugify(title)
    if not slug:
        parser.error("could not derive a slug from the title; pass --slug")

    if args.date:
        when = dt.datetime.fromisoformat(args.date)
        if when.tzinfo is None:
            when = when.replace(tzinfo=dt.datetime.now().astimezone().tzinfo)
    else:
        when = dt.datetime.now().astimezone().replace(microsecond=0)

    langs = [lang.strip() for lang in args.lang.split(",") if lang.strip()]
    unknown = [lang for lang in langs if lang not in languages()]
    if unknown:
        parser.error(f"unknown language(s): {', '.join(unknown)}; configured: {', '.join(languages())}")

    bundle = CONTENT_DIR / f"{when:%Y/%m/%d}" / slug
    bundle.mkdir(parents=True, exist_ok=True)
    safe_title = title.replace('"', '\\"')
    for lang in langs:
        path = bundle / f"index.{lang}.md"
        if path.exists():
            print(f"skip    {path.relative_to(ROOT)} (exists)")
            continue
        path.write_text(TEMPLATE.format(title=safe_title, date=when.isoformat(), slug=slug), encoding="utf-8")
        print(f"created {path.relative_to(ROOT)}")
    print("Next: translate, add description + tags, set draft: false, then `mise run index`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
