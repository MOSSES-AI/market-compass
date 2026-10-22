#!/usr/bin/env python3
"""Refresh attributed ANTARA RSS headlines; retain last good data on failures.

No article bodies, trading signals, credentials, or paid APIs are used.
"""
import argparse
import concurrent.futures
import datetime as dt
import email.utils
import html
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

UTC = dt.timezone.utc
FEEDS = [
    ("politik", "Politik", "P", "politik"),
    ("ekonomi", "Ekonomi", "E", "ekonomi"),
    ("finansial", "Finansial", "E", "ekonomi-finansial"),
    ("bursa", "Bursa", "E", "ekonomi-bursa"),
    ("humaniora", "Humaniora", "S", "humaniora"),
    ("tekno", "Teknologi", "T", "tekno"),
    ("hukum", "Hukum", "L", "hukum"),
    ("lingkungan", "Lingkungan", "ENV", "warta-bumi"),
    ("dunia", "Dunia / geopolitik", "GEO", "dunia"),
    ("terkini", "Lintas rubrik", "LATEST", "terkini"),
]
MAX_BYTES = 2_000_000
MAX_AGE = dt.timedelta(days=7)
VALID_CATEGORIES = {"P", "E", "S", "T", "L", "ENV", "GEO"}
TITLE_RULES = {
    "P": r"\b(presiden|dpr|partai|pilkada|pemilu|kabinet|tni|diplomasi|kementerian|menteri|wamen\w*)\b",
    "E": r"\b(ihsg|rupiah|kurs|inflasi|bi[- ]rate|bank indonesia|anggaran|apbn|pajak|bursa|ekonomi|fiskal|saham|investasi|mineral|hilirisasi|danantara)\b",
    "S": r"\b(pendidikan|pesantren|kesehatan|kemiskinan|tenaga kerja|buruh|bansos|sekolah|mahasiswa|literasi|stunting|keagamaan|santri)\b",
    "T": r"\b(teknologi|digital|siber|kecerdasan buatan|ai|gim|data center|internet|inovasi)\b",
    "L": r"\b(hukum|putusan|regulasi|undang[- ]undang|peraturan|pengadilan|mahkamah|kpk|korupsi|kejaksaan|penyidikan)\b",
    "ENV": r"\b(lingkungan|iklim|karbon|emisi|deforestasi|banjir|gempa|bencana|energi terbarukan|sampah|hutan)\b",
    "GEO": r"\b(iran|israel|gaza|ukraina|rusia|amerika serikat|china|tiongkok|tarif|perang|nato|timur tengah|selat hormuz|trump)\b",
}


def classify_title(title):
    """Navigation tags only, not sentiment, factual verification, or impact analysis."""
    return sorted(key for key, pattern in TITLE_RULES.items() if re.search(pattern, title, re.IGNORECASE))


def iso(value):
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def timestamp(value):
    try:
        result = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return result.astimezone(UTC) if result.tzinfo else None
    except (ValueError, TypeError):
        return None


def clean_title(value):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", "", value or ""))).strip()[:300]


def valid_link(value):
    try:
        u = urllib.parse.urlsplit(value.strip())
        if u.scheme != "https" or u.hostname not in ("www.antaranews.com", "antaranews.com") or u.username or u.password or u.port:
            return None
        return urllib.parse.urlunsplit((u.scheme, u.hostname, u.path, "", ""))
    except (ValueError, AttributeError):
        return None


def parse_feed(body, feed, now):
    feed_id, label, category, _ = feed
    root = ET.fromstring(body)
    items = []
    for item in root.findall("./channel/item")[:50]:
        title = clean_title(item.findtext("title"))
        link = valid_link(item.findtext("link"))
        try:
            published = email.utils.parsedate_to_datetime(item.findtext("pubDate", "")).astimezone(UTC)
        except (ValueError, TypeError, AttributeError, OverflowError):
            continue
        # Reject future-dated, undated, empty, or old entries instead of inventing freshness.
        if not title or not link or published > now + dt.timedelta(minutes=10) or now - published > MAX_AGE:
            continue
        categories = classify_title(title) if category == "LATEST" else [category]
        if categories:
            items.append({"title": title, "url": link, "published_at": iso(published),
                          "publisher": "ANTARA", "categories": categories, "feeds": [feed_id]})
    return items


def read_url(url):
    request = urllib.request.Request(url, headers={"User-Agent": "MarketCompass/2.0 (public RSS reader)", "Accept": "application/rss+xml, application/xml, application/json"})
    with urllib.request.urlopen(request, timeout=20) as response:
        body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise ValueError("response_too_large")
        return body


def fetch_feed(feed, now):
    feed_id, label, category, slug = feed
    url = f"https://www.antaranews.com/rss/{slug}.xml"
    source = {"id": feed_id, "label": label, "category": category, "url": url, "checked_at": iso(now)}
    try:
        items = parse_feed(read_url(url), feed, now)
        if not items:
            raise ValueError("no_recent_items")
        source.update(status="ok", last_success_at=iso(now), latest_published_at=max(x["published_at"] for x in items), count=len(items))
        return source, items
    except Exception as error:
        source.update(status="error", error=type(error).__name__, count=0, last_success_at=None, latest_published_at=None)
        return source, []


def merge_items(items, now):
    result = {}
    for item in items:
        link = valid_link(item.get("url"))
        published = timestamp(item.get("published_at"))
        title = clean_title(item.get("title"))
        if not link or not title or not published or now - published > MAX_AGE or published > now + dt.timedelta(minutes=10):
            continue
        categories = sorted(set(item.get("categories", [])) & VALID_CATEGORIES)
        feeds = sorted(set(item.get("feeds", [])) & {x[0] for x in FEEDS})
        if not categories or not feeds:
            continue
        if link in result:
            result[link]["categories"] = sorted(set(result[link]["categories"]) | set(categories))
            result[link]["feeds"] = sorted(set(result[link]["feeds"]) | set(feeds))
        else:
            result[link] = {"title": title, "url": link, "published_at": iso(published), "publisher": "ANTARA", "categories": categories, "feeds": feeds}
    # Cap per category, so a high-volume economy feed does not crowd out other PESTLE fields.
    ordered = sorted(result.values(), key=lambda x: x["published_at"], reverse=True)
    selected = set()
    for category in VALID_CATEGORIES:
        selected.update(x["url"] for x in [a for a in ordered if category in a["categories"]][:18])
    return [x for x in ordered if x["url"] in selected]


def build_snapshot(results, previous, now):
    old_sources = {x.get("id"): x for x in previous.get("sources", [])}
    sources, candidates = [], []
    failed = set()
    for source, items in results:
        if source["status"] != "ok":
            failed.add(source["id"])
            old = old_sources.get(source["id"], {})
            source["last_success_at"] = old.get("last_success_at")
            source["latest_published_at"] = old.get("latest_published_at")
        sources.append(source)
        candidates.extend(items)
    # Preserve prior headlines only for feeds that failed this run, keeping their original dates.
    for item in previous.get("items", []):
        kept_feeds = set(item.get("feeds", [])) & failed
        if kept_feeds:
            retained = dict(item, feeds=sorted(kept_feeds))
            retained["categories"] = item.get("categories", []) if "terkini" in kept_feeds else sorted({x[2] for x in FEEDS if x[0] in kept_feeds})
            candidates.append(retained)
    return {"schema_version": 1, "generated_at": iso(now), "schedule": "hourly", "publisher": "ANTARA",
            "method": "Official RSS rubric grouping plus transparent title-keyword tags for latest-news RSS. Headlines only; no automated investment analysis.",
            "sources": sources, "items": merge_items(candidates, now)}


def load_previous(path, previous_url):
    snapshots = []
    if path.exists():
        try:
            snapshots.append(json.loads(path.read_text()))
        except (ValueError, OSError):
            pass
    if previous_url:
        try:
            snapshots.append(json.loads(read_url(previous_url)))
        except Exception:
            pass
    snapshots = [x for x in snapshots if isinstance(x, dict) and x.get("schema_version") == 1]
    return max(snapshots, key=lambda x: x.get("generated_at", ""), default={})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/live.json")
    parser.add_argument("--previous-url")
    args = parser.parse_args()
    target = Path(args.output)
    previous = load_previous(target, args.previous_url)
    now = dt.datetime.now(UTC)
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(lambda feed: fetch_feed(feed, now), FEEDS))
    snapshot = build_snapshot(results, previous, now)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(target)
    print(f"News refresh: {sum(s['status'] == 'ok' for s in snapshot['sources'])}/{len(FEEDS)} feeds, {len(snapshot['items'])} attributed headlines, checked {iso(now)}")
    for source in snapshot["sources"]:
        if source["status"] != "ok":
            print(f"::warning::RSS {source['id']}: {source['error']}; last success retained: {source['last_success_at']}")


if __name__ == "__main__":
    main()
