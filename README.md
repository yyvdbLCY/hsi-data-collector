# HSI 數據爬取器 (hsi-data-collector)

跑在 GitHub Actions 的 HSI 數據爬取集,目的: 繞 sandbox 網絡限制,給 hsi-analyst-bot 提供 cache JSON。

## 3 個爬蟲

| 爬蟲 | 頻率 | 輸出 | 用途 |
|---|---|---|---|
| `analyst_ratings` | 每日 1 次 | `cache/analyst_ratings.json` | HSI 18 隻權重股的大行評級 / 目標價 |
| `economic_calendar` | 每日 1 次 | `cache/economic_calendar.json` | 未來 7 天經濟數據發布日曆 |
| `ticker_news` | 每小時 1 次 | `cache/ticker_news.json` | HSI 18 隻權重股的個股新聞 (Google News + Yahoo) |

## 架構

```
sandbox → cron-job.org → repository_dispatch → GitHub Actions → 推 cache/*.json → hsi-analyst-bot 讀取
```

每個爬蟲獨立 workflow,獨立 cache JSON,獨立觸發。

## 觸發器

- `workflow_dispatch` (手動)
- `repository_dispatch` types: `[analyst-ratings]`, `[economic-calendar]`, `[ticker-news]` (cron-job.org 觸發)

不用 GitHub Actions 內建 schedule (不準時)。

## hsi-analyst-bot 整合

每個 cache JSON 由對應的 `lib/xxx.py` 模組讀取,加進 `_build_context`。

## HSI 18 隻權重股清單

滬水 (傳統藍籌): 5 匯豐 / 939 建行 / 1398 工行 / 388 港交所 / 941 中移動 / 883 中海油 / 857 中石油 / 2628 國壽 / 3968 招商
深水 (科技): 700 騰訊 / 9988 阿里 / 3690 美團 / 1810 小米 / 9618 京東 / 9999 網易 / 1024 快手 / 2318 平安 / 1211 比亞迪 / 2899 紫金
