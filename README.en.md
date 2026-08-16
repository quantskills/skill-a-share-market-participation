# A-share Market Participation Analysis

Determine whether an A-share market move reflects broad participation or is being carried by a small group of leaders and crowded themes.

`skill-a-share-market-participation` converts a cross-sectional market snapshot into a reproducible report covering market breadth, turnover concentration, speculative crowding, leader dependence, and structural fragility. It supports intraday monitoring and post-close review.

The output is descriptive research for monitoring and education. It is not a stock picker, an execution tool, investment advice, or a promise of returns.

## What It Measures

The analyzer reports:

- advancing and declining shares, median return, and turnover captured by advancers;
- top 1%, 5%, and 10% turnover concentration, turnover Gini, and effective traded-name count;
- high-return and high-turnover participation, leader dependence, and optional close-location confirmation;
- participation, liquidity distribution, speculation, and fragility scores on 0-100 scales;
- deterministic state labels, risk flags, constructive signals, and optional historical percentiles.

The possible state labels are `broad-participation`, `balanced-rotation`, `narrow-leadership`, `speculative-crowding`, `defensive-contraction`, and `deleveraging-stress`.

## Natural-language Use

In Codex, Claude Code, Cursor, or another compatible agent runtime, ask a market-structure question directly, for example:

> Check whether the latest A-share session was a broad rally or driven by a few leaders.

> Analyze turnover concentration and market breadth from this CSV.

For a live request, the Skill runs the bundled snapshot and analysis scripts. It does not use web search, news pages, or webpage scraping as replacement market data.

## Data Sources

The live-source order is fixed:

1. PandaData is the primary source.
2. AKShare is the fallback when PandaData cannot return a usable snapshot.

A user-provided local CSV is also supported. If both approved live sources fail, the workflow stops and reports the provider or runtime error instead of substituting data from the web.

PandaData credentials can be provided in a local `.env` file or environment variables:

```text
PANDA_DATA_USERNAME=your_username
PANDA_DATA_PASSWORD=your_password
PANDA_DATA_BASE_URL=http://pandadata.pandaaiquant.com
```

Do not commit or distribute real credentials.

## Installation

Python 3.10 or newer is required.

With standard Python:

```bash
python -m pip install -r requirements.txt
```

With `uv`:

```bash
uv sync
```

Dependency installation is normal setup. The restriction on web access applies to replacement market data, not to installing declared packages.

## Live Snapshot

With standard Python:

```bash
python scripts/fetch_akshare_snapshot.py \
  --out a_share_spot.csv \
  --benchmark 沪深300
```

With `uv`:

```bash
uv run --no-sync --no-cache a-share-snapshot \
  --out a_share_spot.csv \
  --benchmark 沪深300
```

The command writes:

```text
a_share_spot.csv
a_share_spot.meta.json
```

Metadata records the observation date, fetch time, provider, row count, and benchmark name.

## Generate a Report

With standard Python:

```bash
python scripts/analyze_market_participation.py a_share_spot.csv \
  --meta a_share_spot.meta.json \
  --out-json report.json \
  --out-md report.md
```

If a historical metrics file is available, add `--history market_history.csv`. Use `--append-history` only after reviewing the current report.

With the installed `uv` entry point:

```bash
uv run --no-sync --no-cache a-share-participation a_share_spot.csv \
  --meta a_share_spot.meta.json \
  --out-json report.json \
  --out-md report.md
```

## Offline Example

The files under `examples/` are synthetic fixtures. They validate the calculation workflow and do not represent a real trading session.

```bash
python scripts/analyze_market_participation.py examples/sample_snapshot.csv \
  --date 2026-08-06 \
  --index-return 0.86 \
  --history examples/sample_history.csv \
  --out-json example-report.json \
  --out-md example-report.md
```

For the bundled synthetic input, the expected state is `narrow-leadership`. Approximate expected scores are:

```text
Participation           45.0
Liquidity distribution  46.4
Speculation              54.1
Fragility risk           68.5
```

## Input and Output Contracts

A minimal local input contains `code`, `pct_change`, and `amount`:

```csv
code,pct_change,amount
600000,6.20,2400000000
600001,5.10,2100000000
600002,-0.80,180000000
```

Optional fields include name, turnover rate, OHLC prices, amplitude, float market capitalization, and industry. See [`references/input-contract.md`](references/input-contract.md) for accepted aliases and units.

The JSON output includes `state`, `scores`, `breadth`, `liquidity_distribution`, `crowding`, `risk_flags`, `constructive_signals`, `top_turnover_names`, `industries`, `history_context`, and `source_meta`. See [`references/output-contract.md`](references/output-contract.md) for the complete contract and [`references/methodology.md`](references/methodology.md) for metric definitions.

## Verification

Run the unit tests:

```bash
python -m unittest discover -s tests -v
```

Run the synthetic example above and confirm that the report is generated and that its values are close to the documented expectations.

Live verification additionally requires checking the metadata trade date, provider, row count, and intraday or post-close status.

## Limitations

- A daily cross-section describes the current session; it does not establish causality or predict the next session.
- Intraday and post-close snapshots are not directly comparable without qualification.
- The speculation score measures intensity, not bullish or bearish direction.
- Daily snapshots cannot establish order-book depth, queue position, bid-ask spread, market impact, or execution quality.
- The Skill does not perform order routing, VWAP/TWAP scheduling, fill simulation, slippage analysis, TCA, or stock-level margin, northbound-flow, and block-trade attribution.

## Community Project Notice

This is a QuantSkills Community Project for quantitative research, market monitoring, and educational examples. It is not an official QuantSkills certification, endorsement, or investment view.

The project is maintained by contributors and reviewers through the upstream repository at `https://github.com/quantskills/skill-a-share-market-participation`.

License: `GPL-3.0-only`.
