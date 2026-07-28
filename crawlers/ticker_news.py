"""
Crawler 3: HSI 18 隻權重股的個股新聞

來源:
- Google News RSS (繁體中文) — 主力
- Yahoo Finance RSS (英文) — 補充

每隻股票抓 5 條最新, 去重, 保留最新的 N 條

輸出: cache/ticker_news.json
{
  "updated": "2026-07-29T09:35:00+08:00",
  "news": {
    "0700.HK": {
      "name": "騰訊控股",
      "items": [
        {
          "title": "...",
          "link": "...",
          "published": "...",
          "source": "..."
        }
      ]
    },
    ...
  }
}

執行: python crawlers/ticker_news.py
"""
import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import quote

import feedparser

HKT = timezone(timedelta(hours=8))

# HSI 18 隻權重股 (跟 analyst_ratings 對齊)
HSI_18 = [
    ("0005.HK", "匯豐控股"),
    ("0939.HK", "建設銀行"),
    ("1398.HK", "工商銀行"),
    ("0388.HK", "港交所"),
    ("0941.HK", "中國移動"),
    ("0883.HK", "中海油"),
    ("0857.HK", "中國石油"),
    ("2628.HK", "中國人壽"),
    ("3968.HK", "招商銀行"),
    ("0700.HK", "騰訊控股"),
    ("9988.HK", "阿里巴巴"),
    ("3690.HK", "美團"),
    ("1810.HK", "小米"),
    ("9618.HK", "京東集團"),
    ("9999.HK", "網易"),
    ("2318.HK", "中國平安"),
    ("1211.HK", "比亞迪股份"),
    ("2899.HK", "紫金礦業"),
]

# 個別股票中英名對照 (提升 Google News 命中)
NAME_EN = {
    "0005.HK": "HSBC Holdings",
    "0939.HK": "China Construction Bank",
    "1398.HK": "ICBC",
    "0388.HK": "HKEX",
    "0941.HK": "China Mobile",
    "0883.HK": "CNOOC",
    "0857.HK": "PetroChina",
    "2628.HK": "China Life Insurance",
    "3968.HK": "China Merchants Bank",
    "0700.HK": "Tencent",
    "9988.HK": "Alibaba",
    "3690.HK": "Meituan",
    "1810.HK": "Xiaomi",
    "9618.HK": "JD.com",
    "9999.HK": "NetEase",
    "2318.HK": "Ping An Insurance",
    "1211.HK": "BYD",
    "2899.HK": "Zijin Mining",
}


def fetch_google_news(symbol: str, name_zh: str, name_en: str = "", max_items: int = 5) -> list:
    """從 Google News RSS 抓個股新聞 (繁中)"""
    query = f"{name_zh} {symbol} 港股"
    if name_en:
        query += f" OR {name_en}"
    url = f"https://news.google.com/rss/search?q={quote(query)}&hl=zh-HK&gl=HK&ceid=HK:zh-Hant"
    try:
        feed = feedparser.parse(url)
        items = []
        for entry in feed.entries[:max_items]:
            items.append({
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "source": entry.get("source", {}).get("title", "Google News"),
            })
        return items
    except Exception as e:
        return [{"error": f"google_news: {str(e)[:100]}"}]


def fetch_yahoo_news(symbol: str, max_items: int = 5) -> list:
    """從 Yahoo Finance RSS 抓個股新聞 (英文)"""
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US"
    try:
        feed = feedparser.parse(url)
        items = []
        for entry in feed.entries[:max_items]:
            items.append({
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "source": "Yahoo Finance",
            })
        return items
    except Exception as e:
        return [{"error": f"yahoo_news: {str(e)[:100]}"}]


def merge_news(google: list, yahoo: list, max_total: int = 8) -> list:
    """
    合併 Google + Yahoo 新聞, 去重 (同標題)
    Google 優先 (繁中), Yahoo 補充
    """
    seen_titles = set()
    merged = []
    for item in google + yahoo:
        if "error" in item:
            continue
        title = item.get("title", "").strip()
        if not title:
            continue
        # 簡單去重:標題前 30 字
        key = title[:30]
        if key in seen_titles:
            continue
        seen_titles.add(key)
        merged.append(item)
        if len(merged) >= max_total:
            break
    return merged


def main():
    print(f"[ticker_news] start, {len(HSI_18)} stocks")
    all_news = {}
    for i, (sym, name_zh) in enumerate(HSI_18, 1):
        print(f"  [{i}/{len(HSI_18)}] {sym} {name_zh} ...", end=" ", flush=True)
        name_en = NAME_EN.get(sym, "")
        google = fetch_google_news(sym, name_zh, name_en, max_items=5)
        yahoo = fetch_yahoo_news(sym, max_items=5)
        merged = merge_news(google, yahoo, max_total=8)
        all_news[sym] = {
            "name": name_zh,
            "items": merged,
        }
        print(f"OK {len(merged)} items")
        time.sleep(0.3)

    output = {
        "updated": datetime.now(HKT).isoformat(),
        "news": all_news,
        "count": len(all_news),
    }

    cache_dir = Path(__file__).parent.parent / "cache"
    cache_dir.mkdir(exist_ok=True)
    out_path = cache_dir / "ticker_news.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"[ticker_news] saved {out_path} ({len(all_news)} tickers)")


if __name__ == "__main__":
    main()
