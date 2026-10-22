import datetime as dt
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("news", Path(__file__).resolve().parents[1] / "scripts/update_news.py")
news = importlib.util.module_from_spec(spec)
spec.loader.exec_module(news)
NOW = dt.datetime(2026, 10, 22, 6, tzinfo=dt.timezone.utc)


class NewsTests(unittest.TestCase):
    def item(self, **values):
        item = {"title": "Kebijakan pasar", "url": "https://www.antaranews.com/berita/123/a", "published_at": "2026-10-22T04:00:00Z", "categories": ["E"], "feeds": ["ekonomi"]}
        return dict(item, **values)

    def test_untrusted_links_and_dates_are_rejected(self):
        for link in ("javascript:alert(1)", "https://antaranews.com.evil.test/a", "https://user@www.antaranews.com/a", "https://www.antaranews.com:8443/a"):
            self.assertIsNone(news.valid_link(link))
        entries = [self.item(published_at="2030-01-01T00:00:00Z"), self.item(published_at="2025-01-01T00:00:00Z"), self.item(published_at="bad")]
        self.assertEqual(news.merge_items(entries, NOW), [])

    def test_deduplication_preserves_both_pestle_categories(self):
        result = news.merge_items([self.item(), self.item(categories=["P"], feeds=["politik"])], NOW)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["categories"], ["E", "P"])

    def test_source_failure_retains_original_success_time(self):
        old = {"sources": [{"id": "ekonomi", "last_success_at": "2026-10-22T03:00:00Z", "latest_published_at": "2026-10-22T02:00:00Z"}], "items": [self.item()]}
        result = news.build_snapshot([({"id": "ekonomi", "status": "error", "checked_at": news.iso(NOW)}, [])], old, NOW)
        self.assertEqual(result["sources"][0]["last_success_at"], "2026-10-22T03:00:00Z")
        self.assertEqual(result["items"][0]["published_at"], "2026-10-22T04:00:00Z")
        self.assertEqual(result["sources"][0]["status"], "error")

    def test_rss_skips_missing_date_and_strips_markup(self):
        body = b'<rss><channel><item><title>&lt;b&gt;Berita&lt;/b&gt; &amp;amp; pasar</title><link>https://www.antaranews.com/berita/1/a</link><pubDate>Thu, 22 Oct 2026 11:00:00 +0700</pubDate></item><item><title>Tanpa tanggal</title><link>https://www.antaranews.com/berita/2/b</link></item></channel></rss>'
        result = news.parse_feed(body, news.FEEDS[1], NOW)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Berita & pasar")
        self.assertEqual(result[0]["published_at"], "2026-10-22T04:00:00Z")

    def test_latest_headline_tags_are_literal_and_not_universal(self):
        self.assertEqual(news.classify_title("Presiden bahas peraturan emisi karbon"), ["ENV", "L", "P"])
        self.assertEqual(news.classify_title("Jadwal pertandingan bulu tangkis"), [])


if __name__ == "__main__":
    unittest.main()
