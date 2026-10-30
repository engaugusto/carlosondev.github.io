#!/usr/bin/env python3
"""Generate the home and archive pages for every language.

Python port of akitaonrails.github.io's scripts/generate_index.rb, generalized
to any number of languages (read from hugo.yaml).

Writes, for each language <lang>:
  content/_index.<lang>.md            featured carousel + recent posts by month
  content/archives/_index.<lang>.md   older posts by month

Posts from January of (current year - 1) onward go to the home page; older
ones go to the archive. Mark a post as featured with ``featured: true``.

Usage:
  mise run index                      # normal run
  python scripts/generate_index.py --drafts --future   # local preview only!
  python scripts/generate_index.py --check             # CI: fail if stale
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import sys
from collections import defaultdict
from itertools import groupby

from blog import CONTENT_DIR, Post, language_prefix, languages, select_posts, tag_map

ARCHIVES_DIR = CONTENT_DIR / "archives"
FEATURED_LIMIT = 12
CUTOFF_YEAR = dt.date.today().year - 1

STRINGS = {
    "en": {
        "home_title": "Carlos on Dev",
        "archives_title": "Archives",
        "featured": "Featured",
        "recent": "Recent articles",
        "prev": "Previous featured posts",
        "next": "Next featured posts",
        "of": "of",
        "article": ("article", "articles"),
        "list": "List", "grid": "Grid", "view": "Post view",
        "archive_link": "Browse the full archive →",
        "archive_intro": "Posts published before {year}.",
        "empty_home": "No posts in English yet.",
        "empty_archive": "Nothing in the archive yet.",
        "other_langs": "Read in",
        "months": ["January", "February", "March", "April", "May", "June", "July",
                   "August", "September", "October", "November", "December"],
        "short_date": "{mon} {day:02d}",
        "card_date": "{mon} {day}, {year}",
    },
    "es": {
        "home_title": "Carlos on Dev",
        "archives_title": "Archivo",
        "featured": "Destacados",
        "recent": "Artículos recientes",
        "prev": "Destacados anteriores",
        "next": "Siguientes destacados",
        "of": "de",
        "article": ("artículo", "artículos"),
        "list": "Lista", "grid": "Cuadrícula", "view": "Vista de entradas",
        "archive_link": "Ver el archivo completo →",
        "archive_intro": "Entradas publicadas antes de {year}.",
        "empty_home": "Todavía no hay entradas en español.",
        "empty_archive": "Todavía no hay nada en el archivo.",
        "other_langs": "Leer en",
        "months": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
                   "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
        "short_date": "{day:02d} {mon}",
        "card_date": "{day} {mon} {year}",
    },
    "pt-br": {
        "home_title": "Carlos on Dev",
        "archives_title": "Arquivo",
        "featured": "Destaques",
        "recent": "Artigos recentes",
        "prev": "Destaques anteriores",
        "next": "Próximos destaques",
        "of": "de",
        "article": ("artigo", "artigos"),
        "list": "Lista", "grid": "Grade", "view": "Visualização dos posts",
        "archive_link": "Ver arquivo completo →",
        "archive_intro": "Posts publicados antes de {year}.",
        "empty_home": "Ainda não há posts em português.",
        "empty_archive": "Ainda não há nada no arquivo.",
        "other_langs": "Ler em",
        "months": ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
                   "agosto", "setembro", "outubro", "novembro", "dezembro"],
        "short_date": "{day:02d}/{month:02d}",
        "card_date": "{day:02d}/{month:02d}/{year}",
    },
}

LANGUAGE_LABELS = {"en": "English", "es": "Español", "pt-br": "Português"}


def strings(lang: str) -> dict:
    if lang not in STRINGS:
        sys.exit(f"generate_index.py: add UI strings for language '{lang}' to STRINGS")
    return STRINGS[lang]


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def fmt_date(post: Post, lang: str, key: str) -> str:
    s = strings(lang)
    d = post.date
    return s[key].format(day=d.day, month=d.month, year=d.year, mon=s["months"][d.month - 1][:3])


def count_label(n: int, lang: str) -> str:
    one, many = strings(lang)["article"]
    return f"{n} {one if n == 1 else many}"


# --------------------------------------------------------------------------- render

def render_tags(post: Post, modifier: str) -> str:
    if not post.tags:
        return ""
    prefix = language_prefix(post.lang)
    links = "".join(
        f'<a class="cod-tag-link" href="{esc(f"{prefix}/tags/{tag}/")}">#{esc(tag)}</a>'
        for tag in post.tags
    )
    return f'<span class="cod-post-tags cod-post-tags--{modifier}">{links}</span>'


def group_by_month(posts: list[Post]) -> list[tuple[tuple[int, int], list[Post]]]:
    ordered = sorted(posts, key=lambda p: p.date, reverse=True)
    return [(key, list(items)) for key, items in groupby(ordered, key=lambda p: (p.date.year, p.date.month))]


def render_months(groups, lang: str) -> list[str]:
    s = strings(lang)
    lines: list[str] = []
    for (year, month), posts in groups:
        heading_id = f"cod-month-{year}-{month:02d}"
        lines.append(f'<section class="cod-index-month" aria-labelledby="{heading_id}">')
        lines.append('<div class="cod-index-month__header">')
        lines.append(f'<h2 id="{heading_id}">{esc(s["months"][month - 1])} {year}</h2>')
        lines.append(f"<span>{esc(count_label(len(posts), lang))}</span>")
        lines.append("</div>")
        lines.append('<div class="cod-index-month__posts">')
        for post in posts:
            lines.append(f'<article class="cod-index-row" title="{esc(post.description)}">')
            lines.append(f'<time datetime="{post.date.date().isoformat()}">'
                         f'<span class="cod-row-date">{esc(fmt_date(post, lang, "short_date"))}</span>'
                         f'<span class="cod-card-date">{esc(fmt_date(post, lang, "card_date"))}</span></time>')
            lines.append('<div class="cod-index-row__body">')
            lines.append(f'<h3><a class="cod-index-row__link" href="{esc(post.url)}">{esc(post.title)}</a></h3>')
            if post.description:
                lines.append(f"<p>{esc(post.description)}</p>")
            lines.append("</div>")
            if post.tags:
                lines.append(render_tags(post, "row"))
            lines.append("</article>")
        lines.append("</div>")
        lines.append("</section>")
    return lines


def render_post_list(groups, lang: str) -> list[str]:
    return ['<div id="cod-index-list" class="cod-index-list">', *render_months(groups, lang), "</div>"]


def render_featured(posts: list[Post], lang: str) -> list[str]:
    featured = sorted((p for p in posts if p.featured), key=lambda p: p.date, reverse=True)[:FEATURED_LIMIT]
    if not featured:
        return []
    s = strings(lang)
    visible = min(3, len(featured))
    lines = [
        f'<section class="cod-featured" data-featured-carousel aria-label="{esc(s["featured"])}">',
        '<div class="cod-featured__header">',
        f'<h2>{esc(s["featured"])}</h2>',
        '<div class="cod-featured__controls">',
        f'<span class="cod-featured__counter" aria-live="polite" data-of="{esc(s["of"])}">'
        f'1–{visible} {esc(s["of"])} {len(featured)}</span>',
        f'<button type="button" data-featured-prev aria-label="{esc(s["prev"])}">&#8249;</button>',
        f'<button type="button" data-featured-next aria-label="{esc(s["next"])}">&#8250;</button>',
        "</div>",
        "</div>",
        '<div class="cod-featured__track">',
    ]
    for post in featured:
        lines.append('<article class="cod-featured-card" data-featured-item>')
        lines.append(f'<time datetime="{post.date.date().isoformat()}">{esc(fmt_date(post, lang, "card_date"))}</time>')
        lines.append(f'<h3><a href="{esc(post.url)}">{esc(post.title)}</a></h3>')
        if post.description:
            lines.append(f"<p>{esc(post.description)}</p>")
        if post.tags:
            lines.append(render_tags(post, "card"))
        lines.append("</article>")
    lines += ["</div>", "</section>"]
    return lines


def other_language_links(lang: str, page: str) -> str:
    s = strings(lang)
    links = [
        f'<a href="{language_prefix(other)}/{page}" hreflang="{other}">{LANGUAGE_LABELS.get(other, other)}</a>'
        for other in languages() if other != lang
    ]
    return f'<p class="cod-empty">{esc(s["other_langs"])}: {" · ".join(links)}</p>'


def view_toggle(lang: str) -> str:
    s = strings(lang)
    return f'{{{{< index-view-toggle list="{s["list"]}" grid="{s["grid"]}" label="{s["view"]}" >}}}}'


def frontmatter(title: str, extra: str = "") -> str:
    return f'---\ntitle: "{title}"\n{extra}# GENERATED by scripts/generate_index.py (mise run index). Do not edit.\n---\n'


def generate_home(lang: str, recent: list[Post], has_archive: bool) -> str:
    s = strings(lang)
    groups = group_by_month(recent)
    lines = [frontmatter(s["home_title"])]
    if groups:
        lines += render_featured(recent, lang)
        lines += ['<div class="cod-recent-header">', f'<h2>{esc(s["recent"])}</h2>', view_toggle(lang), "</div>"]
        lines += render_post_list(groups, lang)
    else:
        lines += [f'<p class="cod-empty">{esc(s["empty_home"])}</p>', other_language_links(lang, "")]
    if has_archive:
        lines.append(f'<div class="cod-archive-link"><a href="{language_prefix(lang)}/archives/">'
                     f'{esc(s["archive_link"])}</a></div>')
    return "\n".join(lines) + "\n"


def generate_archives(lang: str, archived: list[Post]) -> str:
    s = strings(lang)
    groups = group_by_month(archived)
    lines = [frontmatter(s["archives_title"])]
    if groups:
        lines.append(f'<p class="cod-listing-intro">{esc(s["archive_intro"].format(year=CUTOFF_YEAR))}</p>')
        lines += render_post_list(groups, lang)
    else:
        lines.append(f'<p class="cod-empty">{esc(s["empty_archive"])}</p>')
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- main

def build_outputs(*, drafts: bool, future: bool) -> dict:
    outputs = {}
    problems: list[str] = []
    for lang in languages():
        posts = select_posts(lang, drafts=drafts, future=future)
        known = tag_map(lang)
        for post in posts:
            unknown = [tag for tag in post.tags if tag not in known]
            if unknown:
                problems.append(f"{post.path.relative_to(CONTENT_DIR.parent)}: unknown {lang} tag(s): "
                                f"{', '.join(unknown)} (mise run tags:search \"...\")")
        recent = [p for p in posts if p.date.year >= CUTOFF_YEAR]
        archived = [p for p in posts if p.date.year < CUTOFF_YEAR]
        outputs[CONTENT_DIR / f"_index.{lang}.md"] = generate_home(lang, recent, bool(archived))
        outputs[ARCHIVES_DIR / f"_index.{lang}.md"] = generate_archives(lang, archived)
        outputs[("count", lang)] = (len(recent), len(archived))
    if problems:
        sys.exit("\n".join(problems))
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--drafts", action="store_true", help="include drafts (local preview only)")
    parser.add_argument("--future", action="store_true", help="include future-dated posts (local preview only)")
    parser.add_argument("--check", action="store_true", help="exit 1 if the generated files are out of date")
    args = parser.parse_args()

    if args.check and (args.drafts or args.future):
        parser.error("--check cannot be combined with --drafts/--future")

    preview = args.drafts or args.future
    if preview:
        print("*** --drafts/--future are for LOCAL PREVIEW ONLY: unpublished posts will be listed in the\n"
              "*** generated _index files. Run `mise run index` again before committing.", file=sys.stderr)

    outputs = build_outputs(drafts=args.drafts, future=args.future)
    files = {path: text for path, text in outputs.items() if not isinstance(path, tuple)}

    if args.check:
        stale = [p for p, text in files.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
        if stale:
            for path in stale:
                print(f"stale: {path.relative_to(CONTENT_DIR.parent)}", file=sys.stderr)
            print("Run `mise run index` and commit the result.", file=sys.stderr)
            return 1
        print(f"Generated index files are up to date ({len(files)} files).")
        return 0

    ARCHIVES_DIR.mkdir(parents=True, exist_ok=True)
    for path, text in files.items():
        path.write_text(text, encoding="utf-8")
    for lang in languages():
        recent, archived = outputs[("count", lang)]
        print(f"[{lang}] home: {recent} posts ({CUTOFF_YEAR}+), archive: {archived} posts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
