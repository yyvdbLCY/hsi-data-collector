"""
Crawler: 經濟日曆 (HSBC 隱藏 API) — 2026-08-30 用戶實測 7 個源後選定

來源: https://www.warrants.hsbc.com.hk/tc/ajax/statistic/hk_calendar?month=XX&year=YYYY
為什麼選 HSBC(2026-08-30 用戶評比):
- 160 筆/月 (vs ForexFactory 0 events 週末)
- 繁中內容 (跟 hsi-analyst-bot brief 語言一致)
- JSON 結構化 (無需 HTML 解析)
- 無反爬蟲 (免費,免 API key)
- 包含: 經濟數據(type=news) + 業績發布(type=result)

過濾邏輯:
- 只保留 type="news" (純經濟數據),排除 type="result" (業績發布)
- 只保留未來 7 天 (符合 brief「未來 7 天重要事件」需求)
- 移除 HTML 標籤,清純文字
- 國家代碼統一大寫 (US / CN / HK / JP / EU 等)

輸出: cache/economic_calendar.json
{
  "updated": "2026-08-30T...",
  "events": [
    {"date": "2026-08-31", "time": "未指定", "country": "US", "title": "CPI m/m", "impact": "medium"},
    ...
  ],
  "count": N,
  "source": "hsbc-warrants-api"
}

執行: python crawlers/economic_calendar.py
頻率: 每日 1 次 (建議 HKT 09:00)
"""
import json
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

HKT = timezone(timedelta(hours=8))

API_TEMPLATE = "https://www.warrants.hsbc.com.hk/tc/ajax/statistic/hk_calendar?month={month}&year={year}"


def fetch_hsbc_month(month: int, year: int) -> list:
    """從 HSBC API 拉指定月份的日曆(原始,含業績)"""
    try:
        r = requests.get(
            API_TEMPLATE.format(month=month, year=year),
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        r.raise_for_status()
        d = r.json()
        if isinstance(d, dict) and "data" in d:
            return d["data"]
        return []
    except Exception as e:
        print(f"  HSBC month={year}-{month:02d} error: {e}")
        return []


def _strip_html(s: str) -> str:
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return s.strip()


COUNTRY_MAP = {
    "us": "US", "usa": "US", "united states": "US",
    "china": "CN", "cn": "CN", "prc": "CN", "中國": "CN",
    "hong kong": "HK", "hk": "HK", "港": "HK",
    "japan": "JP", "jp": "JP", "日本": "JP",
    "euro": "EU", "eu": "EU", "eurozone": "EU", "europe": "EU",
    "uk": "GB", "united kingdom": "GB", "gb": "GB", "britain": "GB",
    "australia": "AU", "au": "AU", "aus": "AU",
    "canada": "CA", "ca": "CA",
    "germany": "DE", "de": "DE", "deutschland": "DE",
}


def _norm_country(raw: str) -> str:
    if not raw:
        return "?"
    k = raw.strip().lower()
    return COUNTRY_MAP.get(k, raw.upper()[:3])


HIGH_IMPACT_KEYWORDS = [
    "cpi", "ppi", "gdp", "非農", "非农", "失業率", "失業", "unemployment",
    "pmi", "ism", "央行", "央行利率", "利率決議", "fed", "fomc", "ecb", "boj", "pbo",
    "retail", "零售", "工業產出", "工業生产", "industrial production",
    "外匯存底", "外匯", "外儲", "外储", "foreign reserves",
    "lpr", "社會融資", "社融", "新增貸款",
    "boe", "rba", "boc",
]
MEDIUM_IMPACT_KEYWORDS = [
    "貿易", "trade", "進口", "進口", "出口", "export", "import",
    "m2", "m1", "m0",
    "產能", "產能利用率", "capacity",
    "新屋", "新屋開工", "housing starts", "building permits",
    "耐用品", "durable goods", "工廠訂單", "factory orders",
    "工業",
]


def _infer_impact(title: str) -> str:
    t = title.lower()
    for kw in HIGH_IMPACT_KEYWORDS:
        if kw.lower() in t:
            return "High"
    for kw in MEDIUM_IMPACT_KEYWORDS:
        if kw.lower() in t:
            return "Medium"
    return "Low"


def main():
    print("[economic_calendar] start (HSBC API)")
    now = datetime.now(HKT)
    today = now.date()
    cutoff = today + timedelta(days=7)

    all_raw = []
    for i in range(2):
        year = now.year
        month = now.month + i
        if month > 12:
            month -= 12
            year += 1
        events = fetch_hsbc_month(month, year)
        print(f"  month {year}-{month:02d}: {len(events)} raw")
        all_raw.extend(events)
        time.sleep(0.3)

    near_term = []
    for ev in all_raw:
        if ev.get("type") != "news":
            continue
        try:
            ev_date = datetime.strptime(ev["date"], "%Y-%m-%d").date()
        except Exception:
            continue
        if not (today <= ev_date <= cutoff):
            continue

        title_clean = _strip_html(ev.get("event", ""))
        if not title_clean:
            continue

        near_term.append({
            "date": ev["date"],
            "time": "未指定",
            "country": _norm_country(ev.get("country", "")),
            "title": title_clean,
            "impact": _infer_impact(title_clean),
        })

    impact_order = {"High": 0, "Medium": 1, "Low": 2}
    near_term.sort(key=lambda x: (x["date"], impact_order.get(x["impact"], 3)))

    print(f"  過濾後 (type=news + 未來 7 天): {len(near_term)} 筆")
    for ev in near_term[:10]:
        print(f"    {ev['date']} [{ev['country']}] {ev['title'][:40]}... [{ev['impact']}]")

    output = {
        "updated": now.isoformat(),
        "events": near_term,
        "count": len(near_term),
        "source": "hsbc-warrants-api",
    }

    cache_dir = Path(__file__).parent.parent / "cache"
    cache_dir.mkdir(exist_ok=True)
    out_path = cache_dir / "economic_calendar.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"[economic_calendar] saved {out_path} ({len(near_term)} events)")


if __name__ == "__main__":
    main()
