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

RSS_FEEDS = [
    'https://www3.nhk.or.jp/rss/news/cat0.xml',
    'https://news.yahoo.co.jp/rss/topics/top-picks.xml',
    'https://jp.reuters.com/world/rss',
    'https://jp.reuters.com/business/rss',
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


def parse_pubdate(pub: str):
    if not pub:
        return None
    for fmt in [
        '%a, %d %b %Y %H:%M:%S %z',
        '%a, %d %b %Y %H:%M:%S %Z',
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%dT%H:%M:%SZ',
    ]:
        try:
            dt = datetime.strptime(pub.strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            continue
    return None


def collect_from_rss():
    items = []

    for feed in RSS_FEEDS:
        try:
            req = urllib.request.Request(feed, headers={'User-Agent': 'daily-news-calendar/1.0'})
            with urllib.request.urlopen(req, timeout=20) as resp:
                xml_data = resp.read()

            root = ET.fromstring(xml_data)

            for item in root.findall('.//item'):
                title = strip_html((item.findtext('title') or '').strip())
                link = (item.findtext('link') or '').strip()
                desc = strip_html(item.findtext('description') or '')
                pub = (item.findtext('pubDate') or item.findtext('dc:date') or '').strip()
                dt = parse_pubdate(pub)

                if not title or not link:
                    continue

                items.append({
                    'title': title,
                    'source': normalize_domain(link),
                    'link': link,
                    'snippet': desc,
                    'publishedAt': dt.isoformat() if dt else None,
                })
        except Exception:
            continue

    return items


def pick_todays_news(items, limit=10):
    today_jst = datetime.now(JST).date()

    todays = []
    for i in items:
        p = i.get('publishedAt')
        if not p:
            continue
        try:
            dt = datetime.fromisoformat(p)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt.astimezone(JST).date() == today_jst:
                todays.append(i)
        except Exception:
            continue

    if len(todays) >= 5:
        items = todays

    items = dedupe(items)
    items.sort(key=lambda x: x.get('publishedAt') or '', reverse=True)
    return items[:limit]


def build_summary(headlines):
    if not headlines:
        return '本日のニュースを取得できませんでした。'
    return '本日公開分を中心に、主要ニュース記事をまとめました。'


def main():
    os.makedirs(ENTRIES_DIR, exist_ok=True)

    collected = collect_from_rss()
    items = pick_todays_news(collected, limit=10)

    payload = {
        'date': TODAY,
        'title': f'{TODAY} のニュースまとめ',
        'summary': build_summary(items),
        'headlines': items,
        'meta': {
            'sourceMode': 'rss',
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

    print(f'Generated: {ENTRY_PATH} (mode={payload["meta"]["sourceMode"]}, items={len(items)})')


if __name__ == '__main__':
    main()
