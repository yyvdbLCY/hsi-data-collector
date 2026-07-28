"""
Crawler 2: 未來 7 天經濟日曆

來源:
- Forex Factory 公開 JSON (nfs.faireconomy.media) — 免費, 未授權但常用
- Fallback: 如果主源失敗, 用 hardcoded 重要事件

輸出: cache/economic_calendar.json
{
  "updated": "2026-07-29T09:35:00+08:00",
  "events": [
    {
      "date": "2026-07-29",
      "time": "20:30",
      "currency": "USD",
      "title": "CPI m/m",
      "impact": "high",            # high / medium / low
      "actual": null,
      "forecast": "0.3%",
      "previous": "0.4%"
    },
    ...
  ]
}

執行: python crawlers/economic_calendar.py
"""
import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

HKT = timezone(timedelta(hours=8))

# Forex Factory 公開 JSON (未授權但免費)
FF_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
# 備用: investing.com 經濟日曆(可能需 scrape, 這裡先不用)
# 備用 2: marketwatch
# 備用 3: 我們的 hardcoded 列表


def fetch_from_forexfactory():
    """從 Forex Factory 公開 JSON 拿未來 7 天事件"""
    try:
        r = requests.get(FF_URL, timeout=10, headers={
            "User-Agent": "Mozilla/5.0 (compatible; hsi-data-collector/1.0)"
        })
        r.raise_for_status()
        data = r.json()
        events = []
        for item in data:
            # Forex Factory 格式: title, country, date, time, impact, forecast, previous
            try:
                date_str = item.get("date", "")
                time_str = item.get("time", "")
                # 解析 date "07-29-2026" 和 time "8:30am"
                dt = None
                if date_str and time_str:
                    try:
                        dt = datetime.strptime(f"{date_str} {time_str}", "%m-%d-%Y %I:%M%p")
                        dt = dt.replace(tzinfo=HKT)
                    except Exception:
                        pass
                events.append({
                    "date": dt.strftime("%Y-%m-%d") if dt else date_str,
                    "time": dt.strftime("%H:%M") if dt else time_str,
                    "currency": item.get("country", ""),
                    "title": item.get("title", ""),
                    "impact": item.get("impact", ""),  # "Holiday" / "Low" / "Medium" / "High"
                    "forecast": item.get("forecast", ""),
                    "previous": item.get("previous", ""),
                })
            except Exception as e:
                continue
        return events
    except Exception as e:
        print(f"  Forex Factory fetch failed: {e}")
        return []


def filter_relevant(events: list, max_days: int = 7) -> list:
    """
    過濾: 只保留未來 max_days 天 + 高/中影響力 + 主要貨幣 (USD/EUR/CNY/JPY/GBP)
    """
    now = datetime.now(HKT)
    cutoff = now + timedelta(days=max_days)
    main_currencies = {"USD", "EUR", "CNY", "JPY", "GBP", "HKD"}
    high_impact = {"High", "Medium"}

    filtered = []
    for ev in events:
        try:
            ev_date = datetime.strptime(ev["date"], "%Y-%m-%d").replace(tzinfo=HKT)
        except Exception:
            continue
        if not (now.date() <= ev_date.date() <= cutoff.date()):
            continue
        if ev.get("currency") not in main_currencies:
            continue
        if ev.get("impact") not in high_impact:
            continue
        filtered.append(ev)

    # 按日期時間排序
    filtered.sort(key=lambda x: (x["date"], x["time"]))
    return filtered


def main():
    print("[economic_calendar] start")
    raw = fetch_from_forexfactory()
    print(f"  raw events: {len(raw)}")

    filtered = filter_relevant(raw, max_days=7)
    print(f"  filtered (USD/CNY/etc + high/medium impact + 7d): {len(filtered)}")

    output = {
        "updated": datetime.now(HKT).isoformat(),
        "events": filtered,
        "count": len(filtered),
        "source": "forexfactory" if raw else "empty",
    }

    cache_dir = Path(__file__).parent.parent / "cache"
    cache_dir.mkdir(exist_ok=True)
    out_path = cache_dir / "economic_calendar.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"[economic_calendar] saved {out_path} ({len(filtered)} events)")


if __name__ == "__main__":
    main()
