"""Site tests. Python port of akitaonrails.github.io's scripts/test_*.rb.

Builds the site once into a temporary directory with Hugo, then checks the
generated HTML/RSS against the posts' front matter.

    mise run test
"""

from __future__ import annotations

import datetime as dt
import email.utils
import html
import json
import re
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from urllib.parse import unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import generate_index  # noqa: E402
from blog import ROOT, all_posts, language_prefix, languages  # noqa: E402

NEXT_POST_RE = re.compile(r'<aside class="cod-next-post.*?<a class="cod-next-post__link" href="([^"]+)"', re.S)
LD_JSON_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)


class SiteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix="carlosondev-test-")
        cls.public = Path(cls._tmp.name)
        cls.build_started = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
        result = subprocess.run(
            ["hugo", "--quiet", "--destination", str(cls.public)],
            cwd=ROOT, capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"hugo build failed:\n{result.stdout}\n{result.stderr}")
        cls.build_finished = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=1)
        cls.posts = [p for p in all_posts() if p.published()]

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def page(self, url: str) -> str:
        path = self.public / unquote(url).strip("/") / "index.html"
        self.assertTrue(path.is_file(), f"missing page {url}")
        return path.read_text(encoding="utf-8")

    # ------------------------------------------------------------------ posts

    def test_every_post_is_built_at_its_url(self):
        self.assertTrue(self.posts, "no published posts found")
        for post in self.posts:
            with self.subTest(post=post.url):
                self.assertIn(post.title, html.unescape(self.page(post.url)))

    def test_next_post_is_chronological(self):
        """Port of test_chronological_next.rb: same language, the closest newer post."""
        checked = 0
        for current in self.posts:
            newer = sorted((p for p in self.posts if p.lang == current.lang and p.date > current.date),
                           key=lambda p: p.date)
            match = NEXT_POST_RE.search(self.page(current.url))
            with self.subTest(post=current.url):
                if not newer:
                    self.assertIsNone(match, "newest post must not recommend anything")
                    continue
                self.assertIsNotNone(match, "should recommend the next post")
                self.assertEqual(unquote(match.group(1)), newer[0].url)
                checked += 1
        self.assertGreater(checked, 0)

    def test_translations_are_linked(self):
        """Each post lists every translation in its hreflang alternates."""
        bundles: dict[Path, list] = {}
        for post in self.posts:
            bundles.setdefault(post.bundle, []).append(post)
        for posts in bundles.values():
            for post in posts:
                page = self.page(post.url)
                for other in posts:
                    with self.subTest(post=post.url, translation=other.lang):
                        self.assertRegex(page, rf'rel="?alternate"? hreflang="?[^ >]+"? href="?[^" >]*{re.escape(other.url)}')

    # ------------------------------------------------------------------ RSS

    def test_rss_dates_match_articles(self):
        """Port of test_rss_dates.rb: RSS pubDate == article datePublished."""
        checked = 0
        for lang in languages():
            xml = (self.public / language_prefix(lang).strip("/") / "index.xml").read_text(encoding="utf-8")
            built = email.utils.parsedate_to_datetime(html.unescape(re.search(r"<lastBuildDate>(.*?)</lastBuildDate>", xml).group(1)))
            # lastBuildDate is the newest post date, never in the future
            self.assertLessEqual(built, self.build_finished, f"{lang}: lastBuildDate in the future")
            items = re.findall(r"<item>(.*?)</item>", xml, re.S)
            self.assertTrue(items, f"{lang}: feed has no items")
            for item in items:
                link = re.search(r"<link>(.*?)</link>", item).group(1)
                page = self.page(urlparse(link).path)
                articles = [json.loads(m) for m in LD_JSON_RE.findall(page)]
                article = next((a for a in articles if a.get("@type") == "BlogPosting"), None)
                if article is None:  # non-post pages (e.g. About) can appear in the feed
                    continue
                expected = dt.datetime.fromisoformat(article["datePublished"])
                actual = email.utils.parsedate_to_datetime(html.unescape(re.search(r"<pubDate>(.*?)</pubDate>", item).group(1)))
                with self.subTest(link=link):
                    self.assertEqual(actual, expected)
                checked += 1
        self.assertGreater(checked, 0)

    # ------------------------------------------------------------------ indexes

    def test_generated_indexes_are_up_to_date(self):
        outputs = generate_index.build_outputs(drafts=False, future=False)
        for path, text in outputs.items():
            if isinstance(path, tuple):
                continue
            with self.subTest(file=str(path.relative_to(ROOT))):
                self.assertTrue(path.exists(), "run `mise run index`")
                self.assertEqual(path.read_text(encoding="utf-8"), text, "stale; run `mise run index`")

    def test_home_lists_recent_posts_and_no_drafts(self):
        cutoff = generate_index.CUTOFF_YEAR
        drafts = [p for p in all_posts() if not p.published()]
        for lang in languages():
            home = self.page(f"{language_prefix(lang)}/")
            for post in self.posts:
                if post.lang == lang and post.date.year >= cutoff:
                    with self.subTest(lang=lang, post=post.url):
                        self.assertIn(f'href="{post.url}"', home)
            for post in drafts:
                with self.subTest(lang=lang, draft=post.url):
                    self.assertNotIn(f'href="{post.url}"', home)

    # ------------------------------------------------------------------ redirects

    def test_root_redirects_by_language(self):
        """Port of test_language_redirects.cjs, for netlify.toml."""
        config = tomllib.loads((ROOT / "netlify.toml").read_text(encoding="utf-8"))
        root_rules = [r for r in config["redirects"] if r["from"] == "/"]
        self.assertTrue(root_rules, "no redirect for /")
        for rule in root_rules:
            self.assertTrue(rule.get("force"), "'/' rules need force=true (public/index.html exists)")
        by_lang = {tuple(r.get("conditions", {}).get("Language", [])): r["to"] for r in root_rules}
        for lang in languages():
            code = lang.split("-")[0]
            if lang == generate_index.languages()[0]:
                continue
            self.assertEqual(by_lang.get((code,)), f"{language_prefix(lang)}/", f"missing / redirect for {lang}")
        self.assertIn((), by_lang, "missing fallback redirect for /")
        self.assertIsNone(root_rules[-1].get("conditions"), "fallback must be the last '/' rule")


if __name__ == "__main__":
    unittest.main()
