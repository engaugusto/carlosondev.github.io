"""Shared helpers for the blog scripts: languages, posts, front matter, tags.

Posts live in ``content/YYYY/MM/DD/<dir>/index.<lang>.md``. A plain ``index.md``
belongs to the default language. Languages, their order and the default
language are read from ``hugo.yaml`` so there is a single source of truth.
"""

from __future__ import annotations

import datetime as dt
import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content"
TAXONOMY_PATH = ROOT / "data" / "tag_taxonomy.yml"
POST_GLOB = "[0-9][0-9][0-9][0-9]/[0-9][0-9]/[0-9][0-9]/*/index*.md"
FRONTMATTER_RE = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.S)


# --------------------------------------------------------------------------- config

@lru_cache(maxsize=1)
def hugo_config() -> dict:
    return yaml.safe_load((ROOT / "hugo.yaml").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def languages() -> list[str]:
    """Language keys ordered by weight, e.g. ['en', 'es', 'pt-br']."""
    langs = hugo_config()["languages"]
    return sorted(langs, key=lambda key: langs[key].get("weight", 0))


def default_language() -> str:
    return hugo_config().get("defaultContentLanguage", languages()[0])


def language_prefix(lang: str) -> str:
    """URL prefix for a language ('' when the default language lives at '/')."""
    cfg = hugo_config()
    if lang == default_language() and not cfg.get("defaultContentLanguageInSubdir"):
        return ""
    return f"/{lang}"


def language_of(path: Path) -> str | None:
    """'index.es.md' -> 'es'; 'index.md' -> default language; unknown -> None."""
    match = re.fullmatch(r"index(?:\.([A-Za-z-]+))?\.md", path.name)
    if not match:
        return None
    lang = (match.group(1) or default_language()).lower()
    return lang if lang in languages() else None


# --------------------------------------------------------------------------- text

def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def normalize(text: str) -> str:
    """Accent-free, lowercase, words separated by single spaces (for search)."""
    return slugify(str(text)).replace("-", " ")


# --------------------------------------------------------------------------- posts

def parse_frontmatter(path: Path) -> dict:
    match = FRONTMATTER_RE.match(path.read_text(encoding="utf-8"))
    if not match:
        raise ValueError(f"{path}: missing YAML front matter")
    return yaml.safe_load(match.group(1)) or {}


def parse_date(value) -> dt.datetime:
    if isinstance(value, dt.datetime):
        result = value
    elif isinstance(value, dt.date):
        result = dt.datetime(value.year, value.month, value.day)
    else:
        result = dt.datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    if result.tzinfo is None:  # Hugo treats naive dates as UTC
        result = result.replace(tzinfo=dt.timezone.utc)
    return result


@dataclass
class Post:
    path: Path
    lang: str
    title: str
    date: dt.datetime
    url: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    draft: bool = False
    featured: bool = False

    @property
    def bundle(self) -> Path:
        return self.path.parent

    def published(self, now: dt.datetime | None = None) -> bool:
        now = now or dt.datetime.now(dt.timezone.utc)
        return not self.draft and self.date <= now


def load_post(path: Path) -> Post | None:
    lang = language_of(path)
    if lang is None:
        return None
    fm = parse_frontmatter(path)
    if not fm.get("title") or not fm.get("date"):
        return None
    rel = path.parent.relative_to(CONTENT_DIR).parts  # (YYYY, MM, DD, dir)
    slug = str(fm.get("slug") or rel[-1])
    url = f"{language_prefix(lang)}/{'/'.join(rel[:-1])}/{slug}/"
    return Post(
        path=path,
        lang=lang,
        title=str(fm["title"]),
        date=parse_date(fm["date"]),
        url=url,
        description=str(fm.get("description") or "").strip(),
        tags=[str(tag) for tag in (fm.get("tags") or [])],
        draft=bool(fm.get("draft", False)),
        featured=bool(fm.get("featured", False)),
    )


def all_posts() -> list[Post]:
    posts = [load_post(path) for path in sorted(CONTENT_DIR.glob(POST_GLOB))]
    return [post for post in posts if post is not None]


def select_posts(lang: str, *, drafts: bool = False, future: bool = False) -> list[Post]:
    now = dt.datetime.now(dt.timezone.utc)
    return [
        post
        for post in all_posts()
        if post.lang == lang
        and (drafts or not post.draft)
        and (future or post.date <= now)
    ]


# --------------------------------------------------------------------------- tags

@lru_cache(maxsize=1)
def taxonomy() -> dict:
    data = yaml.safe_load(TAXONOMY_PATH.read_text(encoding="utf-8")) or {}
    data.setdefault("tags", {})
    return data


def tag_map(lang: str) -> dict[str, str]:
    """Localized tag name -> canonical tag id, for one language."""
    return {values[lang]: tag_id for tag_id, values in taxonomy()["tags"].items() if lang in values}


def tag_name(tag_id: str, lang: str) -> str:
    return taxonomy()["tags"][tag_id][lang]
