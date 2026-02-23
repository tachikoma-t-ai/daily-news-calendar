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

CATEGORIES = [
    {
        'id': 'it-web',
        'name': 'IT関連（Web系ニュース）',
        'queries': [
            'web platform browser release today',
            'social media platform update today',
            'TechCrunch web app browser news',
        ],
    },
    {
        'id': 'it-tech',
        'name': 'IT関連（技術系ニュース）',
        'queries': [
            'software engineering infrastructure open source release',
            'developer tools security update today',
            'cloud native kubernetes release today',
        ],
    },
    {
        'id': 'ai',
        'name': 'AI',
        'queries': [
            'AI model release today',
            'Reuters AI infrastructure news',
            'generative AI enterprise update today',
        ],
    },
    {
        'id': 'crypto',
        'name': '暗号通貨',
        'queries': [
            'CoinDesk Bitcoin Ethereum ETF news today',
            'Bloomberg crypto market news today',
            'crypto regulation SEC news today',
        ],
    },
    {
        'id': 'economy',
        'name': '時事・経済',
        'queries': [
            'Reuters world economy markets today',
            'global markets tariff inflation news today',
            'central bank policy market reaction today',
        ],
    },
    {
        'id': 'real-estate',
        'name': '不動産',
        'queries': [
            'real estate housing market mortgage rates today',
            'property market commercial real estate news today',
            'Reuters real estate market today',
        ],
    },
]

PRIORITY_SOURCES = [
    'reuters.com',
    'bloomberg.com',
    'coindesk.com',
    'apnews.com',
    'nikkei.com',
    'ft.com',
    'wsj.com',
    'techcrunch.com',
    'theverge.com',
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

    if path in ['', '/']:
        return False

    for pat in EXCLUDE_PATTERNS:
        if re.search(pat, lower):
            return False

    if re.search(r'/\d{6,}|/\d{4}/\d{2}/\d{2}|/articles?/', lower):
        return True

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


def fetch_brave(query: str, endpoint: str, count: int = 10):
    qs = urllib.parse.urlencode({'q': query, 'count': count})
    req = urllib.request.Request(
        f'{endpoint}?{qs}',
        headers={
            'Accept': 'application/json',
            'X-Subscription-Token': BRAVE_API_KEY,
        },
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode('utf-8'))


def collect_query_results(query: str):
    items = []

    try:
        payload = fetch_brave(query, BRAVE_NEWS_ENDPOINT, count=10)
        for r in payload.get('results', []):
            title = strip_html(r.get('title', ''))
            link = (r.get('url') or '').strip()
            if not looks_like_article(link):
                continue
            items.append({
                'title': title,
                'link': link,
                'source': normalize_domain(link),
                'snippet': strip_html(r.get('description', '')),
                'publishedHint': (r.get('age') or '').strip(),
            })
    except Exception:
        pass

    if len(items) < 6:
        try:
            payload = fetch_brave(query, BRAVE_WEB_ENDPOINT, count=10)
            for r in payload.get('web', {}).get('results', []):
                title = strip_html(r.get('title', ''))
                link = (r.get('url') or '').strip()
                if not looks_like_article(link):
                    continue
                items.append({
                    'title': title,
                    'link': link,
                    'source': normalize_domain(link),
                    'snippet': strip_html(r.get('description', '')),
                    'publishedHint': (r.get('age') or '').strip(),
                })
        except Exception:
            pass

    return dedupe(items)


def score_item(item):
    s = 0
    src = (item.get('source') or '').lower()
    if src in PRIORITY_SOURCES:
        s += 100
    if item.get('publishedHint'):
        s += 10
    title = (item.get('title') or '').lower()
    if 'live' in title:
        s -= 5
    return s


def split_summary(snippet: str, title: str = ''):
    text = re.sub(r'\s+', ' ', (snippet or '').strip())
    t = (title or '当該ニュース').strip()

    # 要約は必ず日本語2〜3行で返す
    line1 = f'「{t}」に関する最新動向を伝える記事です。'

    if text:
        # 英文スニペットでも日本語文として読める形に包む
        short = text[:90].rstrip(' ,;') + ('…' if len(text) > 90 else '')
        line2 = f'記事概要: {short}'
    else:
        line2 = '記事概要: 速報性の高い話題で、詳細は本文で確認できます。'

    line3 = '影響範囲や今後の展開を把握するため、継続的な確認が重要です。'

    return [line1, line2, line3]


def why_important(category_name: str):
    mapping = {
        'IT関連（Web系ニュース）': 'ユーザー接点（ブラウザ・SNS・Web配信）の変化は、集客とプロダクト戦略に直結するため。',
        'IT関連（技術系ニュース）': '開発生産性・運用コスト・セキュリティ要件に直結し、チームの実装判断へ影響するため。',
        'AI': 'モデル性能だけでなく、供給網・規制・導入ROIの観点で事業インパクトが大きいため。',
        '暗号通貨': 'マクロ要因と資金フローの影響を受けやすく、短期ボラティリティ管理が重要なため。',
        '時事・経済': '金利・為替・関税などの変化が、企業業績と投資判断に広範囲で波及するため。',
        '不動産': '金利・需給・政策変更が、家計・金融・建設関連の景況感に直接効くため。',
    }
    return mapping.get(category_name, '市場と実務の意思決定に影響する可能性があるため。')


def build_section(cat):
    pool = []
    for q in cat['queries']:
        pool.extend(collect_query_results(q))

    pool = dedupe(pool)
    pool = sorted(pool, key=score_item, reverse=True)

    picked = []
    used_domains = set()
    for item in pool:
        domain = item.get('source') or ''
        if domain in used_domains:
            continue
        picked.append(item)
        used_domains.add(domain)
        if len(picked) >= 4:
            break

    if len(picked) < 3:
        for item in pool:
            if item in picked:
                continue
            picked.append(item)
            if len(picked) >= 3:
                break

    section_items = []
    for item in picked[:5]:
        lines = split_summary(item.get('snippet', ''), item.get('title', ''))
        section_items.append({
            'title': item.get('title', ''),
            'summaryLines': lines[:3],
            'whyImportant': why_important(cat['name']),
            'source': item.get('source', ''),
            'link': item.get('link', ''),
        })

    return {
        'id': cat['id'],
        'name': cat['name'],
        'items': section_items,
    }


def build_top3(sections):
    points = []
    for sec in sections:
        if sec.get('items'):
            top = sec['items'][0]
            points.append(f"{sec['name']}：{top['title']}")
    return points[:3]


def main():
    os.makedirs(ENTRIES_DIR, exist_ok=True)

    sections = []
    if BRAVE_API_KEY:
        for cat in CATEGORIES:
            sections.append(build_section(cat))

    headlines = []
    for s in sections:
        for i in s.get('items', []):
            headlines.append({
                'title': i.get('title', ''),
                'source': i.get('source', ''),
                'link': i.get('link', ''),
                'snippet': ' '.join(i.get('summaryLines', [])[:2]),
            })

    payload = {
        'date': TODAY,
        'title': f'{TODAY} の日次ニュースダイジェスト',
        'summary': '6ジャンル（Web系IT / 技術系IT / AI / 暗号通貨 / 時事・経済 / 不動産）で当日ニュースを要約。',
        'sections': sections,
        'top3': build_top3(sections),
        'headlines': headlines[:30],
        'meta': {
            'sourceMode': 'brave' if BRAVE_API_KEY else 'unavailable',
            'categoryCount': len(CATEGORIES),
            'itemCount': sum(len(s.get('items', [])) for s in sections),
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

    print(
        f'Generated: {ENTRY_PATH} '
        f'(mode={payload["meta"]["sourceMode"]}, items={payload["meta"]["itemCount"]})'
    )


if __name__ == '__main__':
    main()
