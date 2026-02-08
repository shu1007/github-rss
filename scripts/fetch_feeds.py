#!/usr/bin/env python3
"""RSSフィードを取得してHTMLを生成するスクリプト."""

import json
import re
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
from time import mktime

import feedparser


def load_feeds(feeds_path: str) -> list[dict]:
    with open(feeds_path, encoding="utf-8") as f:
        return json.load(f)


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def fetch_articles(feeds: list[dict], cutoff: datetime) -> list[dict]:
    articles = []
    for feed_info in feeds:
        url = feed_info["url"]
        source_name = feed_info["name"]
        labels = feed_info.get("labels", [])
        try:
            d = feedparser.parse(url)
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            continue

        for entry in d.entries:
            published = None
            for date_field in ("published_parsed", "updated_parsed"):
                t = getattr(entry, date_field, None)
                if t:
                    published = datetime.fromtimestamp(mktime(t), tz=timezone.utc)
                    break

            if published is None or published < cutoff:
                continue

            summary_raw = getattr(entry, "summary", "") or ""
            summary_text = strip_html(summary_raw).strip()
            if len(summary_text) > 200:
                summary_text = summary_text[:200] + "..."

            articles.append(
                {
                    "title": getattr(entry, "title", "(no title)"),
                    "link": getattr(entry, "link", "#"),
                    "source": source_name,
                    "labels": labels,
                    "published": published,
                    "summary": summary_text,
                }
            )

    articles.sort(key=lambda a: a["published"], reverse=True)
    return articles


def collect_all_labels(articles: list[dict]) -> list[str]:
    labels = set()
    for a in articles:
        labels.update(a["labels"])
    return sorted(labels)


REPO = "shu1007/github-rss"

ISSUE_TEMPLATE_BODY = """\
### Feed URL
(RSSフィードのURLを入力)

### Feed Name
(表示名を入力)

### Labels
(カンマ区切りでラベルを入力。例: tech, news)
"""


def generate_html(articles: list[dict], updated_at: datetime) -> str:
    updated_str = updated_at.strftime("%Y-%m-%d %H:%M UTC")
    all_labels = collect_all_labels(articles)

    from urllib.parse import quote
    issue_url = (
        f"https://github.com/{REPO}/issues/new"
        f"?title={quote('add-feed')}"
        f"&body={quote(ISSUE_TEMPLATE_BODY)}"
        f"&labels={quote('add-feed')}"
    )

    # フィルターボタン
    filter_buttons = ['      <button class="filter-btn active" data-label="all">All</button>']
    for label in all_labels:
        filter_buttons.append(
            f'      <button class="filter-btn" data-label="{escape(label)}">{escape(label)}</button>'
        )
    filters_html = "\n".join(filter_buttons)

    # 記事一覧
    rows = []
    for a in articles:
        pub_str = a["published"].strftime("%Y-%m-%d %H:%M")
        labels_attr = " ".join(a["labels"])
        label_spans = " ".join(
            f'<span class="label">{escape(l)}</span>' for l in a["labels"]
        )
        rows.append(f"""      <article class="entry" data-labels="{escape(labels_attr)}">
        <div class="meta">
          <span class="source">{escape(a['source'])}</span>
          {label_spans}
        </div>
        <h2><a href="{escape(a['link'])}" target="_blank" rel="noopener">{escape(a['title'])}</a></h2>
        <time>{escape(pub_str)}</time>
        <p>{escape(a['summary'])}</p>
      </article>""")

    entries_html = "\n".join(rows) if rows else '      <p>記事がありません。</p>'

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>RSS Reader</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f5f5; color: #333; line-height: 1.6; }}
    .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
    header {{ margin-bottom: 24px; }}
    header h1 {{ font-size: 1.5rem; }}
    header .updated {{ font-size: 0.85rem; color: #888; margin-top: 4px; }}
    .filters {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px; }}
    .filter-btn {{ background: #fff; border: 1px solid #ddd; border-radius: 20px; padding: 6px 16px; font-size: 0.85rem; cursor: pointer; transition: all 0.2s; }}
    .filter-btn:hover {{ border-color: #1a73e8; color: #1a73e8; }}
    .filter-btn.active {{ background: #1a73e8; color: #fff; border-color: #1a73e8; }}
    .entry {{ background: #fff; border-radius: 8px; padding: 16px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
    .entry.hidden {{ display: none; }}
    .entry .meta {{ display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }}
    .entry .source {{ display: inline-block; background: #e8f0fe; color: #1a73e8; font-size: 0.75rem; padding: 2px 8px; border-radius: 4px; font-weight: 600; }}
    .entry .label {{ display: inline-block; background: #f0f0f0; color: #555; font-size: 0.7rem; padding: 2px 8px; border-radius: 4px; }}
    .add-feed {{ display: inline-block; background: #34a853; color: #fff; text-decoration: none; font-size: 0.85rem; padding: 6px 16px; border-radius: 20px; font-weight: 600; transition: background 0.2s; }}
    .add-feed:hover {{ background: #2d8e47; }}
    .entry h2 {{ font-size: 1.1rem; margin: 8px 0 4px; }}
    .entry h2 a {{ color: #1a1a1a; text-decoration: none; }}
    .entry h2 a:hover {{ text-decoration: underline; }}
    .entry time {{ font-size: 0.8rem; color: #888; }}
    .entry p {{ font-size: 0.9rem; color: #555; margin-top: 8px; }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>RSS Reader</h1>
      <div class="updated">Last updated: {updated_str}</div>
      <a class="add-feed" href="{issue_url}" target="_blank" rel="noopener">+ Add Feed</a>
    </header>
    <div class="filters">
{filters_html}
    </div>
    <main>
{entries_html}
    </main>
  </div>
  <script>
    document.querySelectorAll('.filter-btn').forEach(btn => {{
      btn.addEventListener('click', () => {{
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const label = btn.dataset.label;
        document.querySelectorAll('.entry').forEach(entry => {{
          if (label === 'all' || entry.dataset.labels.split(' ').includes(label)) {{
            entry.classList.remove('hidden');
          }} else {{
            entry.classList.add('hidden');
          }}
        }});
      }});
    }});
  </script>
</body>
</html>
"""


def main():
    root = Path(__file__).resolve().parent.parent
    feeds_path = root / "feeds.json"
    docs_dir = root / "docs"
    docs_dir.mkdir(exist_ok=True)
    output_path = docs_dir / "index.html"

    feeds = load_feeds(str(feeds_path))
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=7)

    print(f"Fetching {len(feeds)} feeds...")
    articles = fetch_articles(feeds, cutoff)
    print(f"Found {len(articles)} articles within the last 7 days.")

    html = generate_html(articles, now)
    output_path.write_text(html, encoding="utf-8")
    print(f"Generated {output_path}")


if __name__ == "__main__":
    main()
