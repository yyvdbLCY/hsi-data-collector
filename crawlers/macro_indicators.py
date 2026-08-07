"""
Crawler: 宏觀指標 (2026-08-07 為 hsi-analyst-bot brief 加的關鍵宏觀數據)

抓的指標:
- USD/HKD (港元匯率) — 資金離港警號
- USD/CNH (離岸人民幣) — 人民幣貶值壓力
- 創業板指 (399006.SZ) — 內資情緒領先指標
- A50 期貨 (CN50) — A 股情緒
- VIX (^VIX) — 恐慌指數
- DXY (DX-Y.NYB) — 美元指數
- US10Y (^TNX) — 美 10 年期國債

輸出: cache/macro_indicators.json
{
  "updated": "2026-08-07T13:10:00+08:00",
  "indicators": {
    "usd_hkd": {"price": 7.8234, "change_pct": 0.05, "signal": "neutral"},
    "chinext": {"price": 2150.0, "change_pct": -1.85, "signal": "warning"},
    ...
  }
}

執行: python crawlers/macro_indicators.py
頻率: 每日 4 次 (對齊 brief 09:35/11:35/14:35/16:35 HKT)
"""
import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yfinance as yf

HKT = timezone(timedelta(hours=8))

# yfinance ticker + 解讀閾值
MACRO_TICKERS = {
    # === 用戶 2026-08-07 明確要求 ===
    "usd_hkd": {
        "ticker": "HKD=X",          # yfinance 用 HKD=X
        "threshold_high": 7.80,      # 升穿 = 資金離港警號
        "threshold_alert": 7.81,     # 升穿 = 高警號
        "threshold_low": 7.75,       # 跌穿 = 資金流入
        "interpretation": "資金離港警號",
    },
    "chinext": {
        "ticker": "399006.SZ",       # 深交所創業板指
        "threshold_warn": -1.5,      # 跌 > 1.5% 內資看空
        "threshold_alert": -3.0,     # 跌 > 3% 內資恐慌
        "threshold_bull": 1.5,       # 升 > 1.5% 內資樂觀
        "interpretation": "內資情緒領先指標",
    },
    "a50": {
        "ticker": "CN50",            # FTSE China A50 Index 期貨
        "interpretation": "A 股情緒",
    },
    # === 已有但用 cache 更穩 ===
    "vix": {
        "ticker": "^VIX",
        "threshold_high": 25,        # 升穿 = 恐慌
        "threshold_alert": 30,       # 升穿 = 極度恐慌
        "interpretation": "恐慌指數",
    },
    "dxy": {
        "ticker": "DX-Y.NYB",
        "interpretation": "美元指數",
    },
    "us10y": {
        "ticker": "^TNX",
        "threshold_high": 4.5,       # 升穿 = 流動性收緊
        "interpretation": "美 10 年期國債",
    },
    "usd_cnh": {
        "ticker": "CNH=X",           # 離岸人民幣
        "threshold_alert": 7.30,     # 升穿 = 人民幣貶值壓力
        "interpretation": "離岸人民幣",
    },
}


def _classify(name: str, ind: dict) -> str:
    """根據閾值給出 signal"""
    if "error" in ind or ind.get("change_pct") is None:
        return "unknown"
    cfg = MACRO_TICKERS[name]
    change = ind.get("change_pct", 0)
    price = ind.get("price", 0)

    if name == "usd_hkd":
        if price >= cfg["threshold_alert"]:
            return "alert"
        if price >= cfg["threshold_high"]:
            return "warning"
        if price <= cfg["threshold_low"]:
            return "bullish"
        return "neutral"

    if name == "chinext":
        if change <= cfg["threshold_alert"]:
            return "alert"
        if change <= cfg["threshold_warn"]:
            return "warning"
        if change >= cfg["threshold_bull"]:
            return "bullish"
        return "neutral"

    if name == "vix":
        if price >= cfg["threshold_alert"]:
            return "alert"
        if price >= cfg["threshold_high"]:
            return "warning"
        return "neutral"

    if name == "us10y":
        if price >= cfg["threshold_high"]:
            return "warning"
        return "neutral"

    if name == "usd_cnh":
        if price >= cfg["threshold_alert"]:
            return "alert"
        return "neutral"

    return "neutral"


def fetch_macro() -> dict:
    """抓所有宏觀指標"""
    indicators = {}
    for name, cfg in MACRO_TICKERS.items():
        ticker = cfg["ticker"]
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="5d", interval="1d")
            if hist is None or hist.empty:
                # fallback: try fast_info
                try:
                    price = t.fast_info.get("lastPrice") or t.fast_info.get("last_price")
                    if price:
                        indicators[name] = {
                            "ticker": ticker,
                            "price": round(float(price), 4),
                            "change_pct": None,
                            "interpretation": cfg["interpretation"],
                        }
                        continue
                except Exception:
                    pass
                indicators[name] = {"ticker": ticker, "error": "no data", "interpretation": cfg["interpretation"]}
                continue
            latest = hist.iloc[-1]
            prev = hist.iloc[-2] if len(hist) >= 2 else None
            change_pct = None
            if prev is not None and prev["Close"] and prev["Close"] != 0:
                change_pct = round((latest["Close"] - prev["Close"]) / prev["Close"] * 100, 2)
            ind = {
                "ticker": ticker,
                "price": round(float(latest["Close"]), 4),
                "change_pct": change_pct,
                "interpretation": cfg["interpretation"],
            }
            ind["signal"] = _classify(name, ind)
            indicators[name] = ind
        except Exception as e:
            indicators[name] = {
                "ticker": ticker,
                "error": str(e)[:150],
                "interpretation": cfg["interpretation"],
            }
        time.sleep(0.4)  # 避免 Yahoo rate limit
    return indicators


def main():
    print(f"[macro_indicators] start, {len(MACRO_TICKERS)} indicators")
    indicators = fetch_macro()
    print(f"  fetched: {len([k for k, v in indicators.items() if 'error' not in v])}/{len(MACRO_TICKERS)}")

    for name, ind in indicators.items():
        if "error" in ind:
            print(f"  ⚠️  {name}: {ind['error'][:80]}")
        else:
            sig = ind.get("signal", "?")
            emoji = {"alert": "🔴", "warning": "🟡", "bullish": "🟢", "neutral": "⚪", "unknown": "❓"}.get(sig, "⚪")
            print(f"  {emoji} {name}: {ind.get('price', '?')} ({ind.get('change_pct', '?')}% {sig})")

    output = {
        "updated": datetime.now(HKT).isoformat(),
        "indicators": indicators,
        "count": len(indicators),
    }

    cache_dir = Path(__file__).parent.parent / "cache"
    cache_dir.mkdir(exist_ok=True)
    out_path = cache_dir / "macro_indicators.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"[macro_indicators] saved {out_path} ({len(indicators)} indicators)")


if __name__ == "__main__":
    main()
