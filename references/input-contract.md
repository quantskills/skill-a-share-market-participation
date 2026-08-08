# Input Contract

## Table of contents

- Required columns
- Optional columns
- Accepted aliases
- Units
- Industry enrichment
- History file
- Data-quality rules

## Required columns

The analyzer requires one row per active A-share security and these fields:

| Canonical field | Meaning | Unit |
|---|---|---|
| `code` | Security code | string |
| `pct_change` | Session/intraday percentage change | percent, e.g. `2.4` = +2.4% |
| `amount` | Traded amount | currency units, normally CNY |

Rows with a missing code, missing return, missing turnover, or `amount <= 0` are excluded from active-universe metrics.

## Optional columns

| Field | Used for |
|---|---|
| `name` | Human-readable top-turnover tables |
| `turnover_rate` | High-turnover participation and speculation intensity |
| `amplitude` | Cross-sectional speculative intensity |
| `high`, `low`, `close` | Close-location value for leader confirmation/fade |
| `open`, `prev_close` | Preserved for downstream inspection |
| `float_market_cap` | Small-cap turnover share |
| `total_market_cap` | Downstream market-cap analysis |
| `industry` | Industry turnover/participation aggregation |

## Accepted aliases

The analyzer recognizes the canonical English names and common AKShare/Eastmoney Chinese names, including:

- `代码` → `code`
- `名称` → `name`
- `涨跌幅` → `pct_change`
- `成交额` / `金额` → `amount`
- `换手率` / `换手` → `turnover_rate`
- `振幅` → `amplitude`
- `最新价` / `收盘` → `close`
- `最高`, `最低`, `今开`, `昨收`
- `流通市值`, `总市值`

## Units

Keep percentage fields in percentage points, not decimal returns. For example, use `3.5` for +3.5%, not `0.035`.

The scoring logic uses turnover **shares**, so `amount` can be CNY, thousands of CNY, or another consistent positive unit as long as every row uses the same unit.

## Industry enrichment

Industry is optional. Supply it directly in the snapshot or pass a second CSV:

```bash
python scripts/analyze_market_participation.py snapshot.csv \
  --industry-map industry_map.csv
```

`industry_map.csv` needs only `code,industry` (or accepted Chinese aliases). The analyzer aggregates turnover share, name breadth, and amount-weighted return by industry.

## History file

A history CSV is optional and contains one row per prior session. The analyzer itself can maintain this file with `--append-history`.

Expected fields are:

```text
date,participation_score,liquidity_distribution_score,speculation_score,fragility_score,positive_share,amount_positive_share,top10_turnover_share,turnover_gini,state
```

Historical percentile ranks are descriptive context. They are not p-values and do not imply statistical significance.

## Data-quality rules

- Prefer the same universe definition every day.
- Do not mix post-close snapshots with mid-session snapshots in the same history without labeling them separately.
- Keep suspended/zero-turnover securities out of the active traded universe.
- If using an external industry mapping, align codes as strings and preserve leading zeroes.
- Record the provider and observation timestamp when the snapshot is not bundled with the report.
