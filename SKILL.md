---
name: skill-a-share-market-participation
description: Analyze A-share cross-sectional market participation, turnover concentration, liquidity distribution, speculative crowding, leader dependence, and structural fragility from daily or intraday stock snapshots. Use when the user asks in Chinese or English to analyze A-share market breadth, participation, turnover concentration, crowding, whether an index rally is broad or narrow, or to generate a reproducible market-structure report. Use only bundled scripts with PandaData as the primary live source, AKShare as fallback, or user-provided local data; never search, browse, or scrape webpages for replacement market data, and fail closed when approved sources are unavailable. Do not use for order routing, fill simulation, slippage/TCA, live trade execution, or stock-level margin/northbound/block-trade capital-flow attribution.
license: GPL-3.0-only
metadata:
  organization: QuantSkills
  organization_url: https://github.com/quantskills
  repository: skill-a-share-market-participation
  repository_url: https://github.com/quantskills/skill-a-share-market-participation
  project_type: skill
---

# A-share Market Participation

## Mission

Convert an A-share market snapshot into a reproducible description of **who is participating, where turnover is concentrated, whether leaders are carrying the tape, and how fragile the apparent market move is**.

Keep the scope separate from execution microstructure. Do not design order schedules, model fills, estimate slippage, route orders, or perform TCA. This skill analyzes the market-wide cross-sectional structure of trading activity, not the mechanics of executing a parent order or stock-level margin/northbound/block-trade capital flows.

## Project status and maintenance

Treat this repository as a QuantSkills Community Project, not as an official, certified, verified, endorsed, or production-ready QuantSkills project.

The project is maintained by contributors and reviewers through the upstream repository at `https://github.com/quantskills/skill-a-share-market-participation`. Preserve authorship and contribution history when modifying or redistributing it.

## Natural-language interaction

Understand requests such as “分析今天 A 股是普涨还是少数龙头带动”, “看看成交额集中在哪里”, “抓取今天的 A 股参与度报告”, and “比较今天和最近历史的市场广度”. Reply in the user's language, infer reasonable defaults from available files, and ask only for missing information required to run the requested analysis.

For a live request, use PandaData first. Load credentials from the project's `.env` when available, report the observation date and data source, and fall back to AKShare only when PandaData cannot produce a usable snapshot. Treat the result as descriptive market monitoring, not an investment recommendation.

For requests containing “最近一天”, “今天”, “最新”, or equivalent live wording, always execute the bundled fetch script during the current request. Do not treat existing files such as `a_share_spot.csv`, `a_share_spot.meta.json`, `report.json`, or `report.md` in the project directory as fresh data unless the user explicitly identifies them as the input. Verify the generated metadata's trade date, fetch time, row count, and provider before analyzing it.

## Data-source policy

Use only these inputs:

1. PandaData through the bundled snapshot script.
2. AKShare through the bundled snapshot script when PandaData fails.
3. A local CSV supplied by the user or bundled under `examples/` for an explicitly offline demonstration.

Never use web search, browser tools, news pages, search engines, manually scraped webpages, or unrelated public APIs to replace unavailable snapshot data. If PandaData and AKShare both fail, or the runtime cannot import their dependencies, stop and report the exact provider/runtime error. Do not estimate breadth from news articles and do not present stale example data as the latest session.

Do not recursively search the user's home directory for old snapshots, reports, or unrelated Python environments as a substitute for the current fetch. Existing `examples/` files are synthetic offline fixtures only and must never be labeled as the latest market session.

## Execution requirements

Run bundled commands from the Skill root. After the one-time environment setup, prefer `uv run --no-sync --no-cache`, for example `uv run --no-sync --no-cache a-share-snapshot` or `uv run --no-sync --no-cache python scripts/test_pandadata_login.py`. For distributions where only Python is available, use the target interpreter directly, for example `python scripts/fetch_akshare_snapshot.py` and `python scripts/analyze_market_participation.py`. Do not assume that the system Python already contains `pandas`, `panda-data`, or `akshare`, and do not require `uv` as a hard prerequisite.

Treat dependency installation from `uv.lock`, `pyproject.toml`, or `requirements.txt` as normal Skill setup, not as market-data browsing. When dependencies are missing, automatically run `uv sync` once if `uv` is available; otherwise run `python -m pip install -r requirements.txt`. Do not ask a conversational question before installing declared dependencies. If the execution sandbox requires network or filesystem approval, request that approval directly and retry the same install command. After the environment is complete, use `uv run --no-sync --no-cache` for repeated commands so every request does not re-resolve packages or touch a problematic uv cache.

Treat an import or package-download error as an environment failure, not permission to switch data sources outside the policy above. Do not force offline mode, search the user's home directory for unrelated interpreters or cached market files, or replace declared dependencies with ad hoc packages. If installation still fails after the permitted retry, stop with the exact error.

## Standard workflow

1. **Establish the observation point.** Prefer a post-close snapshot for daily review. If the snapshot is intraday, label every conclusion provisional.
2. **Normalize the universe.** Require `code`, `pct_change`, and `amount`; accept common PandaData and AKShare Chinese aliases. Exclude rows with non-positive turnover or unusable returns. Read [references/input-contract.md](references/input-contract.md) when the input schema is unclear.
3. **Run the deterministic analyzer.** Execute `scripts/analyze_market_participation.py` rather than recomputing scores manually.
4. **Contextualize the session.** If a history CSV is available, pass it through `--history` so the report includes percentile ranks versus prior sessions. Use `--append-history` only after the current report is accepted.
5. **Inspect concentration and participation together.** A rising index with weak name breadth, high top-decile turnover concentration, or large capital-breadth divergence is a narrow move even if headline indices are positive.
6. **Inspect crowding and fragility.** Separate speculation from participation. High speculation can coexist with broad participation, while fragility increases when turnover, leadership, and capital are concentrated in a small slice of the universe.
7. **Produce the standard report.** Return the state label, four scores, key structural metrics, triggered flags, highest-turnover names, optional industry participation, historical percentiles, and guardrails.

## Preferred commands

Analyze a canonical or raw AKShare-style CSV:

```bash
uv run a-share-participation snapshot.csv \
  --date 2026-08-07 \
  --index-return 0.82 \
  --history market_history.csv \
  --out-json report.json \
  --out-md report.md
```

Fetch a live A-share snapshot with PandaData first, then analyze it:

```bash
uv sync
uv run --no-sync --no-cache a-share-snapshot --out a_share_spot.csv --benchmark 沪深300
uv run --no-sync --no-cache a-share-participation a_share_spot.csv \
  --meta a_share_spot.meta.json \
  --out-json report.json \
  --out-md report.md
```

Use the bundled example for an offline smoke test:

```bash
uv run a-share-participation examples/sample_snapshot.csv \
  --date 2026-08-06 \
  --index-return 0.86 \
  --history examples/sample_history.csv \
  --out-json /tmp/a-share-participation.json \
  --out-md /tmp/a-share-participation.md
```

## Result contract

Always surface these sections, even when some optional fields are unavailable:

1. **State** — one of `broad-participation`, `balanced-rotation`, `narrow-leadership`, `speculative-crowding`, `defensive-contraction`, or `deleveraging-stress`.
2. **Scorecard** — participation, liquidity distribution, speculation, and fragility risk on 0–100 scales.
3. **Breadth** — advancer share, turnover in advancers, median return, and large-move share.
4. **Liquidity concentration** — top 1% / 5% / 10% turnover share, turnover Gini, and effective traded-name count.
5. **Leadership/crowding** — top-return-decile turnover share, top-turnover-decile return spread, high-turnover share, and close-location confirmation when available.
6. **Flags** — deterministic risk flags and constructive signals. Do not invent a flag not emitted by the analyzer unless clearly labeled as qualitative commentary.
7. **History context** — percentile rank versus prior sessions when a history file is supplied.
8. **Data quality and guardrails** — dropped rows, missing optional fields, intraday/post-close status, and non-predictive interpretation.

## Interpretation rules

- Treat the four scores as **descriptive heuristics**, not forecasts, target weights, or trade signals.
- Prefer relative historical context over absolute score thresholds. The same turnover concentration can mean different things across market regimes.
- Distinguish **breadth** from **capital breadth**. Equal-weight participation and turnover-weighted participation answer different questions.
- Treat `turnover-concentration` plus `leader-dependence` as a stronger warning than either flag alone.
- Treat a positive index return with `index-up-breadth-weak` as a narrow-index rally, not evidence that the whole market is healthy.
- Do not call high `speculation_score` bearish or bullish by itself. It measures intensity, not direction.
- Do not compare intraday and post-close snapshots as if they were equivalent.
- Do not infer order-book liquidity, queue position, spread capture, market impact, or fill quality from these cross-sectional metrics.

## Reference routing

- Read [references/input-contract.md](references/input-contract.md) for accepted columns, aliases, units, and optional industry enrichment.
- Read [references/methodology.md](references/methodology.md) for metric definitions, score construction, state labels, flags, and limitations.
- Read [references/output-contract.md](references/output-contract.md) when formatting a user-facing report or integrating the JSON output downstream.
