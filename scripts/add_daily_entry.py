#!/usr/bin/env python3
import json
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))
TODAY = datetime.now(JST).strftime('%Y-%m-%d')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, 'data')
ENTRIES_DIR = os.path.join(DATA_DIR, 'entries')
INDEX_PATH = os.path.join(DATA_DIR, 'index.json')
ENTRY_PATH = os.path.join(ENTRIES_DIR, f'{TODAY}.json')

BRAVE_API_KEY = os.getenv('BRAVE_API_KEY', '').strip()
BRAVE_ENDPOINT = 'https://api.search.brave.com/res/v1/web/search'

BRAVE_QUERIES = [
    '最新 IT ニュース 日本',
    'software engineering news',
    '日本 経済 ニュース 今日',
    'crypto market news today',
]

RSS_FALLBACK_FEEDS = [
    'https://news.google.com/rss?hl=ja&gl=JP&ceid=JP:ja',
    'https://www3.nhk.or.jp/rss/news/cat0.xml',
]


def strip_html(s: str) -> str:
    return re.sub(r'<[^>]+>', '', s or '').strip()


def normalize_domain(url: str) -> str:
    try:
        return urllib.parse.urlparse(url).netloc.lower().replace('www.', '')
    except Exception:
        return ''


def dedupe(items):
    seen_title = set()
    seen_link = set()
    out = []
    for i in items:
        t = (i.get('title') or '').strip()
        l = (i.get('link') or '').strip()
        if not t:
            continue
        key_t = t.lower()
        if key_t in seen_title:
            continue
        if l and l in seen_link:
            continue
        seen_title.add(key_t)
        if l:
            seen_link.add(l)
        out.append(i)
    return out


def diversify_by_source(items, limit=10):
    out = []
    seen_domain = set()

    for i in items:
        d = normalize_domain(i.get('link', ''))
        if d and d in seen_domain:
            continue
        out.append(i)
        if d:
            seen_domain.add(d)
        if len(out) >= limit:
            return out

    for i in items:
        if i in out:
            continue
        out.append(i)
        if len(out) >= limit:
            break

    return out


def fetch_brave(query: str):
    qs = urllib.parse.urlencode({
        'q': query,
        'count': 8,
        'search_lang': 'ja',
        'country': 'JP'
    })
    req = urllib.request.Request(
        f'{BRAVE_ENDPOINT}?{qs}',
        headers={
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip',
            'X-Subscription-Token': BRAVE_API_KEY,
        },
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode('utf-8'))


def collect_from_brave():
    items = []
    for q in BRAVE_QUERIES:
        try:
            payload = fetch_brave(q)
            results = payload.get('web', {}).get('results', [])
            for r in results:
                title = strip_html(r.get('title', ''))
                link = (r.get('url') or '').strip()
                source = normalize_domain(link)
                desc = strip_html(r.get('description', ''))
                if title and link:
                    items.append({
                        'title': title,
                        'source': source,
                        'link': link,
                        'snippet': desc,
                    })
        except Exception:
            continue
    return items


def fetch_rss(url: str):
    with urllib.request.urlopen(url, timeout=20) as resp:
        return resp.read()


def parse_rss_items(xml_bytes: bytes):
    items = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return items

    for item in root.findall('.//item')[:20]:
        title = strip_html(item.findtext('title') or '')
        source = strip_html(item.findtext('source') or '')
        link = (item.findtext('link') or '').strip()
        desc = strip_html(item.findtext('description') or '')
        if title:
            items.append({'title': title, 'source': source, 'link': link, 'snippet': desc})
    return items


def collect_from_rss_fallback():
    items = []
    for f in RSS_FALLBACK_FEEDS:
        try:
            items.extend(parse_rss_items(fetch_rss(f)))
        except Exception:
            continue
    return items


def build_summary(headlines, used_brave):
    if not headlines:
        return '本日のニュースを取得できませんでした。後でもう一度更新してください。'
    if used_brave:
        return 'Brave Search APIから主要ニュースを横断収集しました。ソースの偏りを抑えて表示しています。'
    return 'RSSフォールバックでニュースを収集しました。BRAVE_API_KEYを設定すると多様なソースから取得できます。'


def main():
    os.makedirs(ENTRIES_DIR, exist_ok=True)

    used_brave = False
    if BRAVE_API_KEY:
        collected = collect_from_brave()
        used_brave = len(collected) > 0
    else:
        collected = []

    if not collected:
        collected = collect_from_rss_fallback()

    items = diversify_by_source(dedupe(collected), limit=10)

    payload = {
        'date': TODAY,
        'title': f'{TODAY} のニュースまとめ',
        'summary': build_summary(items, used_brave),
        'headlines': items,
        'meta': {
            'sourceMode': 'brave' if used_brave else 'rss-fallback',
            'itemCount': len(items),
        },
        'generatedAt': datetime.now(timezone.utc).isoformat(),
    }

    with open(ENTRY_PATH, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    if os.path.exists(INDEX_PATH):
        with open(INDEX_PATH, 'r', encoding='utf-8') as f:
            index = json.load(f)
    else:
        index = {'entries': {}}

    index.setdefault('entries', {})
    index['entries'][TODAY] = f'data/entries/{TODAY}.json'
    index['entries'] = dict(sorted(index['entries'].items()))

    with open(INDEX_PATH, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f'Generated: {ENTRY_PATH} (mode={payload["meta"]["sourceMode"]})')


if __name__ == '__main__':
    main()
