# Methodology

## Table of contents

- Scope
- Core metrics
- Scores
- State labels
- Deterministic flags
- Historical context
- Limitations

## Scope

This skill analyzes **cross-sectional market participation and turnover structure**. It is deliberately different from execution microstructure, which studies order books, spreads, queues, fills, routing, and transaction costs.

The methodology uses same-snapshot information only. It does not estimate future returns and does not require future data.

## Core metrics

### Breadth

- **Positive share**: number of active securities with positive return / active securities.
- **Amount-positive share**: turnover in positive-return securities / total turnover.
- **Median return**: cross-sectional median percentage change.
- **Large-move share**: fraction of names with absolute return of at least 5%.

### Liquidity concentration

- **Top-k turnover share**: turnover captured by the top 1%, 5%, or 10% of names ranked by `amount`.
- **Turnover Gini**: Gini coefficient of cross-sectional turnover; higher values mean more concentration.
- **HHI / effective names**: `HHI = sum(weight_i^2)` and `effective_names = 1 / HHI`, where `weight_i` is each name's turnover share.

### Leadership and crowding

- **Hot-return-decile turnover share**: turnover inside the top 10% of names ranked by return.
- **Weak-return-decile turnover share**: turnover inside the bottom 10% of names ranked by return.
- **Leadership spread**: turnover-weighted return of the top-turnover decile minus median return of the remaining universe.
- **Close-location value (CLV)**: `(close - low) / (high - low)`, clipped to `[0,1]`. A low CLV among the hottest names indicates intraday fade.
- **High-turnover share**: share of names with `turnover_rate >= 10%`, when available.

## Scores

All scores are 0–100 deterministic heuristics. Thresholds are intentionally transparent and are designed for monitoring, not fitted prediction.

### Participation score

Combines:

- equal-weight positive breadth;
- turnover-weighted positive breadth;
- alignment between name breadth and capital breadth.

Higher means more names and more traded capital are participating in the same direction.

### Liquidity distribution score

Combines the inverse of:

- top-10% turnover concentration;
- turnover Gini;
- low effective-name ratio.

Higher means trading activity is distributed across more securities.

### Speculation score

Combines available components:

- large-move share;
- hot-return-decile turnover share;
- high-turnover-name share;
- median amplitude.

High speculation is not intrinsically bullish or bearish.

### Fragility score

Combines:

- turnover concentration;
- divergence between equal-weight and amount-weighted breadth;
- absolute leadership spread;
- low effective-name ratio;
- leader intraday fade when OHLC fields are available.

Higher means the observed tape depends more heavily on a small or unstable subset of names.

## State labels

The deterministic classifier emits one label:

- `broad-participation`: high participation with limited fragility.
- `balanced-rotation`: neither broad expansion nor structural stress dominates.
- `narrow-leadership`: headline strength or activity is carried by a concentrated subset.
- `speculative-crowding`: speculative intensity and fragility are simultaneously elevated.
- `defensive-contraction`: participation is weak without extreme crowding stress.
- `deleveraging-stress`: participation is very weak and fragility is high.

## Deterministic flags

Potential risk flags include:

- `turnover-concentration`
- `capital-breadth-divergence`
- `index-up-breadth-weak`
- `leader-dependence`
- `speculative-crowding`
- `leader-intraday-fade`
- `broad-risk-off`
- `selloff-liquidity-cluster`

Constructive signals include:

- `broad-participation`
- `distributed-liquidity`
- `capital-breadth-alignment`
- `leader-close-confirmation`

Use combinations of signals instead of treating one threshold as a standalone trading rule.

## Historical context

When prior sessions are supplied, the analyzer reports empirical percentile ranks for the four scores and selected raw metrics. The current date is excluded before percentile calculation to avoid self-comparison.

Percentile rank answers: "How high is today's value relative to the stored history?" It does not establish predictive significance.

## Limitations

- A one-day cross-section cannot identify causality.
- Eastmoney/AKShare snapshots are a data-access convenience, not an exchange-grade market-data feed.
- Turnover concentration is sensitive to universe composition, listings, suspensions, and market-cap regime.
- A daily snapshot cannot recover order-book imbalance, hidden liquidity, queue priority, adverse selection, or implementation shortfall.
- Fixed heuristic thresholds should be calibrated to the user's own historical distribution before production use.
- This skill is for research and monitoring and does not constitute investment advice.
