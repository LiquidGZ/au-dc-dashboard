#!/usr/bin/env python3
"""
fetch_news.py — poll the RSS feeds listed in the workbook's NewsSources sheet (via site/data/news_sources.json)
and merge new headlines into site/data/news.json. Standard library only. Run daily by GitHub Actions.

    python scripts/build_data.py     # first, so news_sources.json reflects the workbook
    python scripts/fetch_news.py

Behaviour
  * keeps items newer than meta.news_days_to_keep (default 90) and at most meta.news_max_items (default 300)
  * de-duplicates by link and by normalised title
  * optional filter_keywords per source (any keyword, case-insensitive, matched on title+summary)
  * tags each item with operators / states it mentions so the site can filter
  * never fails the build: a feed that errors is logged and skipped; the existing news.json is preserved
"""
import datetime as dt
import email.utils
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "data")
NEWS_PATH = os.path.join(DATA, "news.json")
UA = "Mozilla/5.0 (compatible; au-dc-dashboard-news/1.0)"

STATE_WORDS = {
    "NSW": ["nsw", "new south wales", "sydney", "western sydney", "kemps creek", "eastern creek", "newcastle", "hunter"],
    "VIC": ["victoria", "melbourne", "geelong", "tullamarine", "truganina", "derrimut", "south morang"],
    "QLD": ["queensland", "brisbane", "gold coast", "sunshine coast", "ipswich", "townsville"],
    "WA": ["western australia", "perth", "kwinana", "pilbara"],
    "SA": ["south australia", "adelaide"],
    "TAS": ["tasmania", "hobart", "launceston", "bell bay"],
    "ACT": ["canberra", "act "],
    "NT": ["northern territory", "darwin"],
}


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return default


def fetch(url, timeout=40):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml, application/xml, text/xml, */*"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def text(el, *names):
    for n in names:
        x = el.find(n)
        if x is not None and (x.text or "").strip():
            return html.unescape(re.sub(r"<[^>]+>", " ", x.text)).strip()
    return ""


def parse_date(s):
    if not s:
        return None
    try:
        d = email.utils.parsedate_to_datetime(s)
    except (TypeError, ValueError):
        try:
            d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d.astimezone(dt.timezone.utc)


def parse_feed(raw):
    """Return list of dicts from RSS 2.0 or Atom."""
    root = ET.fromstring(raw)
    items = []
    ns = {"atom": "http://www.w3.org/2005/Atom", "media": "http://search.yahoo.com/mrss/"}
    for it in root.iter("item"):  # RSS
        link = text(it, "link") or (it.find("guid").text if it.find("guid") is not None else "")
        src_el = it.find("source")
        items.append({
            "title": text(it, "title"),
            "link": (link or "").strip(),
            "summary": text(it, "description")[:400],
            "published": parse_date(text(it, "pubDate", "{http://purl.org/dc/elements/1.1/}date")),
            "publisher": (src_el.text.strip() if src_el is not None and src_el.text else ""),
        })
    for e in root.iter("{http://www.w3.org/2005/Atom}entry"):  # Atom
        link_el = e.find("atom:link", ns)
        items.append({
            "title": text(e, "atom:title".replace("atom:", "{http://www.w3.org/2005/Atom}")),
            "link": (link_el.get("href") if link_el is not None else "").strip(),
            "summary": text(e, "{http://www.w3.org/2005/Atom}summary", "{http://www.w3.org/2005/Atom}content")[:400],
            "published": parse_date(text(e, "{http://www.w3.org/2005/Atom}published", "{http://www.w3.org/2005/Atom}updated")),
            "publisher": "",
        })
    return items


def norm_title(t):
    t = re.sub(r"\s+-\s+[^-]{2,60}$", "", t)  # strip trailing " - Publisher" that Google News appends
    return re.sub(r"[^a-z0-9一-鿿]+", " ", t.lower()).strip()


def tag_item(title, summary, operators):
    blob = f"{title} {summary}".lower()
    ops = [o["name"] for o in operators if o.get("name") and o["name"].lower() in blob]
    states = [s for s, words in STATE_WORDS.items() if any(w in blob for w in words)]
    return ops, states


def main():
    sources = load_json(os.path.join(DATA, "news_sources.json"), [])
    meta = load_json(os.path.join(DATA, "meta.json"), {})
    operators = load_json(os.path.join(DATA, "operators.json"), [])
    keep_days = int(meta.get("news_days_to_keep") or 90)
    max_items = int(meta.get("news_max_items") or 300)

    existing = load_json(NEWS_PATH, {"items": []})
    items = {i["link"]: i for i in existing.get("items", []) if i.get("link")}
    seen_titles = {norm_title(i["title"]) for i in items.values()}
    now = dt.datetime.now(dt.timezone.utc)
    added, errors = 0, []

    for s in sources:
        if not s.get("enabled", True) or s.get("type", "rss") != "rss":
            continue
        try:
            raw = fetch(s["url"])
            feed_items = parse_feed(raw)
        except (urllib.error.URLError, ET.ParseError, TimeoutError, OSError) as e:
            errors.append(f"{s.get('source_id')}: {e}")
            print(f"  skip {s.get('source_id')}: {e}", file=sys.stderr)
            continue
        kws = [k.lower() for k in (s.get("filter_keywords") or [])]
        n = 0
        for it in feed_items:
            if not it["title"] or not it["link"]:
                continue
            if kws and not any(k in (it["title"] + " " + it["summary"]).lower() for k in kws):
                continue
            nt = norm_title(it["title"])
            if it["link"] in items or nt in seen_titles:
                continue
            pub = it["published"] or now
            if (now - pub).days > keep_days:
                continue
            ops, states = tag_item(it["title"], it["summary"], operators)
            title = it["title"]
            publisher = it["publisher"]
            m = re.search(r"\s-\s([^-]{2,60})$", title)
            if not publisher and m and "news.google" in s["url"]:
                publisher, title = m.group(1).strip(), title[: m.start()].strip()
            items[it["link"]] = {
                "title": title, "link": it["link"], "summary": it["summary"], "publisher": publisher,
                "published": pub.strftime("%Y-%m-%dT%H:%M:%SZ"), "source_id": s.get("source_id"),
                "language": s.get("language", "en"), "operators": ops, "states": states,
                "fetched": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
            seen_titles.add(nt)
            n += 1
        added += n
        print(f"  {s.get('source_id'):16s} {len(feed_items):4d} in feed, {n:3d} new")

    out = sorted(items.values(), key=lambda i: i["published"], reverse=True)
    cutoff = (now - dt.timedelta(days=keep_days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = [i for i in out if i["published"] >= cutoff][:max_items]
    os.makedirs(DATA, exist_ok=True)
    with open(NEWS_PATH, "w", encoding="utf-8") as fh:
        json.dump({"fetched_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "added_this_run": added,
                   "errors": errors, "items": out}, fh, ensure_ascii=False, indent=1)
    print(f"news.json: {len(out)} items ({added} new, {len(errors)} feed errors)")


if __name__ == "__main__":
    main()
