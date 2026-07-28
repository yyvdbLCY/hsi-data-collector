"""
Crawler 1: HSI 18 隻權重股的大行評級 / 目標價

來源: yfinance (Yahoo Finance) `Ticker.info` 與 `Ticker.analysis`

輸出: cache/analyst_ratings.json
{
  "updated": "2026-07-29T09:35:00+08:00",
  "stocks": [
    {
      "symbol": "0700.HK",
      "name": "騰訊控股",
      "current_price": 425.6,
      "target_mean": 510.0,
      "target_low": 380.0,
      "target_high": 600.0,
      "recommendation": "buy",        # buy / hold / sell
      "num_analysts": 32,
      "upside_pct": 19.83            # 計算: (target_mean - current) / current * 100
    },
    ...
  ]
}

執行: python crawlers/analyst_ratings.py (GitHub Actions 內)
"""
import json
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yfinance as yf

HKT = timezone(timedelta(hours=8))

# HSI 18 隻權重股 (去 1024 快手, 跟用戶 2026-07-28 確認)
HSI_18 = [
    # 滬水 (傳統藍籌, 9 隻)
    ("0005.HK", "匯豐控股"),
    ("0939.HK", "建設銀行"),
    ("1398.HK", "工商銀行"),
    ("0388.HK", "港交所"),
    ("0941.HK", "中國移動"),
    ("0883.HK", "中海油"),
    ("0857.HK", "中國石油"),
    ("2628.HK", "中國人壽"),
    ("3968.HK", "招商銀行"),
    # 深水 (科技, 9 隻)
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


def fetch_one(symbol: str, name: str) -> dict:
    """抓單隻股票的大行評級"""
    try:
        t = yf.Ticker(symbol)
        info = t.info or {}

        current = info.get("currentPrice") or info.get("regularMarketPrice")
        target_mean = info.get("targetMeanPrice")
        target_low = info.get("targetLowPrice")
        target_high = info.get("targetHighPrice")
        rec = info.get("recommendationKey")  # "buy" / "hold" / "sell"
        num = info.get("numberOfAnalystOpinions")

        upside = None
        if current and target_mean:
            upside = round((target_mean - current) / current * 100, 2)

        return {
            "symbol": symbol,
            "name": name,
            "current_price": current,
            "target_mean": target_mean,
            "target_low": target_low,
            "target_high": target_high,
            "recommendation": rec,
            "num_analysts": num,
            "upside_pct": upside,
        }
    except Exception as e:
        return {
            "symbol": symbol,
            "name": name,
            "error": str(e)[:200],
        }


def main():
    print(f"[analyst_ratings] start, {len(HSI_18)} stocks")
    stocks = []
    for i, (sym, name) in enumerate(HSI_18, 1):
        print(f"  [{i}/{len(HSI_18)}] {sym} {name} ...", end=" ", flush=True)
        data = fetch_one(sym, name)
        if "error" in data:
            print(f"FAIL: {data['error'][:80]}")
        else:
            upside = data.get("upside_pct")
            print(f"OK target={data.get('target_mean')} upside={upside}%")
        stocks.append(data)
        time.sleep(0.5)  # 避免 Yahoo rate limit

    output = {
        "updated": datetime.now(HKT).isoformat(),
        "stocks": stocks,
        "count": len(stocks),
    }

    # 寫到 cache/analyst_ratings.json
    cache_dir = Path(__file__).parent.parent / "cache"
    cache_dir.mkdir(exist_ok=True)
    out_path = cache_dir / "analyst_ratings.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"[analyst_ratings] saved {out_path} ({len(stocks)} stocks)")


if __name__ == "__main__":
    main()
