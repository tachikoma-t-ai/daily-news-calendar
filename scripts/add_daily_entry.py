#!/usr/bin/env python3
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))
TODAY = datetime.now(JST).strftime('%Y-%m-%d')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, 'data')
ENTRIES_DIR = os.path.join(DATA_DIR, 'entries')
INDEX_PATH = os.path.join(DATA_DIR, 'index.json')
ENTRY_PATH = os.path.join(ENTRIES_DIR, f'{TODAY}.json')

BRAVE_API_KEY = os.getenv('BRAVE_API_KEY', '').strip()
BRAVE_WEB_ENDPOINT = 'https://api.search.brave.com/res/v1/web/search'
BRAVE_NEWS_ENDPOINT = 'https://api.search.brave.com/res/v1/news/search'

BRAVE_QUERIES = [
    '今日 ニュース 主要',
    '日本 国内 ニュース 今日',
    '経済 ニュース 今日',
    'IT ニュース 今日',
    'world news today',
]

EXCLUDE_PATTERNS = [
    r'/categories?/',
    r'/topics?/',
    r'/news/?$',
    r'/top/?$',
    r'/home/?$',
    r'/tag/',
    r'/search',
]


def strip_html(s: str) -> str:
    return re.sub(r'<[^>]+>', '', s or '').strip()


def normalize_domain(url: str) -> str:
    try:
        return urllib.parse.urlparse(url).netloc.lower().replace('www.', '')
    except Exception:
        return ''


def looks_like_article(url: str) -> bool:
    if not url or not url.startswith('http'):
        return False

    lower = url.lower()
    parsed = urllib.parse.urlparse(lower)
    path = (parsed.path or '').strip()

    # トップページは除外
    if path in ['', '/']:
        return False

    for pat in EXCLUDE_PATTERNS:
        if re.search(pat, lower):
            return False

    # 記事っぽいURLを優先（数字IDや日付を含む）
    if re.search(r'/\d{6,}|/\d{4}/\d{2}/\d{2}|/articles?/', lower):
        return True

    # ある程度パスが深いものは許可
    if path.count('/') >= 2:
        return True

    return False


def dedupe(items):
    seen_title = set()
    seen_link = set()
    out = []
    for i in items:
        t = (i.get('title') or '').strip()
        l = (i.get('link') or '').strip()
        if not t or not l:
            continue
        key_t = t.lower()
        if key_t in seen_title or l in seen_link:
            continue
        seen_title.add(key_t)
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


def fetch_brave(query: str, endpoint: str, count: int = 12):
    qs = urllib.parse.urlencode({
        'q': query,
        'count': count,
    })
    req = urllib.request.Request(
        f'{endpoint}?{qs}',
        headers={
            'Accept': 'application/json',
            'X-Subscription-Token': BRAVE_API_KEY,
        },
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode('utf-8'))


def collect_from_brave():
    items = []

    for q in BRAVE_QUERIES:
        # 1) まず news endpoint を優先
        try:
            payload = fetch_brave(q, BRAVE_NEWS_ENDPOINT, count=15)
            results = payload.get('results', [])
            for r in results:
                title = strip_html(r.get('title', ''))
                link = (r.get('url') or '').strip()
                source = normalize_domain(link)
                desc = strip_html(r.get('description', ''))
                age = (r.get('age') or '').strip()
                if title and link and looks_like_article(link):
                    items.append({
                        'title': title,
                        'source': source,
                        'link': link,
                        'snippet': desc,
                        'publishedHint': age,
                    })
        except Exception:
            pass

        # 2) 不足時のみ web endpoint で補完
        if len(items) < 10:
            try:
                payload = fetch_brave(q, BRAVE_WEB_ENDPOINT, count=10)
                results = payload.get('web', {}).get('results', [])
                for r in results:
                    title = strip_html(r.get('title', ''))
                    link = (r.get('url') or '').strip()
                    if not looks_like_article(link):
                        continue
                    source = normalize_domain(link)
                    desc = strip_html(r.get('description', ''))
                    age = (r.get('age') or '').strip()
                    if title and link:
                        items.append({
                            'title': title,
                            'source': source,
                            'link': link,
                            'snippet': desc,
                            'publishedHint': age,
                        })
            except Exception:
                pass

    return items


def build_summary(headlines):
    if not headlines:
        return '本日のニュースを取得できませんでした。'
    return 'Brave Searchで本日の主要ニュース記事を収集しました。'


def main():
    os.makedirs(ENTRIES_DIR, exist_ok=True)

    collected = []
    if BRAVE_API_KEY:
        collected = collect_from_brave()

    items = diversify_by_source(dedupe(collected), limit=10)

    payload = {
        'date': TODAY,
        'title': f'{TODAY} のニュースまとめ',
        'summary': build_summary(items),
        'headlines': items,
        'meta': {
            'sourceMode': 'brave' if BRAVE_API_KEY else 'unavailable',
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
