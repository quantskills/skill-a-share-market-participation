# Output Contract

## Markdown report

Use this section order:

1. Title and report date
2. State label
3. Scorecard
4. Participation structure
5. Liquidity concentration
6. Crowding and leadership
7. Risk flags and constructive signals
8. Highest-turnover names
9. Industry participation, when available
10. Interpretation guardrails

Do not replace measured values with qualitative labels. Put the numeric evidence before interpretation.

## JSON report

The analyzer emits these top-level keys:

```text
date
coverage
breadth
liquidity_distribution
crowding
scores
state
risk_flags
constructive_signals
index_return_pct
top_turnover_names
industries
history_context
source_meta (only when --meta is provided)
```

Downstream consumers should use `scores`, `state`, and raw metric groups rather than parsing the Markdown report.

## Recommended narrative

Prefer compact evidence-led wording such as:

> The index rose, but only 41% of active names advanced and the top 10% of names absorbed 48% of turnover. Participation is narrow and liquidity is leader-dependent, so the tape is classified as `narrow-leadership` rather than broad risk-on.

Avoid wording such as "the market will fall tomorrow" or "buy the leaders" because the metrics describe current structure rather than future returns.
