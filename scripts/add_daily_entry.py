#!/usr/bin/env python3
import json
import os
import re
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

FEEDS = [
    'https://news.google.com/rss?hl=ja&gl=JP&ceid=JP:ja',
    'https://www3.nhk.or.jp/rss/news/cat0.xml',
]


def strip_html(s: str) -> str:
    return re.sub(r'<[^>]+>', '', s or '').strip()


def fetch_rss(url: str):
    with urllib.request.urlopen(url, timeout=20) as resp:
        return resp.read()


def parse_items(xml_bytes: bytes):
    items = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return items

    for item in root.findall('.//item')[:20]:
        title = strip_html(item.findtext('title') or '')
        source = strip_html(item.findtext('source') or '')
        link = (item.findtext('link') or '').strip()
        if title:
            items.append({'title': title, 'source': source, 'link': link})
    return items


def dedupe(items):
    seen = set()
    out = []
    for i in items:
        key = i['title']
        if key in seen:
            continue
        seen.add(key)
        out.append(i)
    return out


def build_summary(headlines):
    if not headlines:
        return '本日のニュースを取得できませんでした。後でもう一度更新してください。'
    tops = headlines[:5]
    return '主要ニュースを自動収集しました。注目トピックは次の通りです。'


def main():
    os.makedirs(ENTRIES_DIR, exist_ok=True)

    all_items = []
    for f in FEEDS:
        try:
            all_items.extend(parse_items(fetch_rss(f)))
        except Exception:
            continue

    items = dedupe(all_items)[:10]

    payload = {
        'date': TODAY,
        'title': f'{TODAY} のニュースまとめ',
        'summary': build_summary(items),
        'headlines': items,
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

    # Sort by date string
    index['entries'] = dict(sorted(index['entries'].items()))

    with open(INDEX_PATH, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f'Generated: {ENTRY_PATH}')


if __name__ == '__main__':
    main()
