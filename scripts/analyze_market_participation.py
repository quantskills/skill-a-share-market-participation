#!/usr/bin/env python3
"""Analyze A-share cross-sectional participation, crowding, and structural fragility."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import date as date_cls
from pathlib import Path
from typing import Any, Iterable

ALIASES = {
    "code": ["code", "代码", "证券代码"],
    "name": ["name", "名称", "证券简称"],
    "pct_change": ["pct_change", "涨跌幅", "涨幅"],
    "amount": ["amount", "成交额", "金额"],
    "turnover_rate": ["turnover_rate", "换手率", "换手"],
    "amplitude": ["amplitude", "振幅"],
    "high": ["high", "最高"],
    "low": ["low", "最低"],
    "open": ["open", "今开"],
    "close": ["close", "最新价", "收盘"],
    "prev_close": ["prev_close", "昨收", "前收盘"],
    "float_market_cap": ["float_market_cap", "流通市值"],
    "total_market_cap": ["total_market_cap", "总市值"],
    "industry": ["industry", "行业", "所属行业"],
}

KEY_HISTORY_FIELDS = [
    "participation_score",
    "liquidity_distribution_score",
    "speculation_score",
    "fragility_score",
    "positive_share",
    "amount_positive_share",
    "top10_turnover_share",
    "turnover_gini",
]


def clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def scale_up(x: float, lo: float, hi: float) -> float:
    if hi <= lo:
        return 0.0
    return clamp((x - lo) / (hi - lo) * 100.0)


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if text in {"", "-", "--", "nan", "NaN", "None", "null"}:
        return None
    if text.endswith("%"):
        text = text[:-1]
    try:
        result = float(text)
    except ValueError:
        return None
    if not math.isfinite(result):
        return None
    return result


def find_field(headers: Iterable[str], canonical: str) -> str | None:
    header_set = {h.strip(): h for h in headers if h is not None}
    for alias in ALIASES[canonical]:
        if alias in header_set:
            return header_set[alias]
    return None


def gini(values: list[float]) -> float:
    xs = sorted(x for x in values if x >= 0)
    if not xs or sum(xs) <= 0:
        return 0.0
    n = len(xs)
    weighted = sum((i + 1) * x for i, x in enumerate(xs))
    return (2.0 * weighted) / (n * sum(xs)) - (n + 1.0) / n


def weighted_mean(rows: list[dict[str, Any]], value_key: str, weight_key: str = "amount") -> float | None:
    pairs = []
    for row in rows:
        v = row.get(value_key)
        w = row.get(weight_key)
        if v is not None and w is not None and w > 0:
            pairs.append((float(v), float(w)))
    if not pairs:
        return None
    total = sum(w for _, w in pairs)
    return sum(v * w for v, w in pairs) / total if total else None


def pct_rank(current: float, history: list[float]) -> float | None:
    vals = [x for x in history if math.isfinite(x)]
    if not vals:
        return None
    return 100.0 * sum(1 for x in vals if x <= current) / len(vals)


@dataclass
class Snapshot:
    rows: list[dict[str, Any]]
    dropped_rows: int
    source_rows: int
    columns: dict[str, str | None]


def load_snapshot(path: Path, industry_map: Path | None = None) -> Snapshot:
    industry_lookup: dict[str, str] = {}
    if industry_map:
        with industry_map.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise ValueError("industry map has no header")
            code_col = find_field(reader.fieldnames, "code")
            industry_col = find_field(reader.fieldnames, "industry")
            if not code_col or not industry_col:
                raise ValueError("industry map must contain code and industry columns")
            for row in reader:
                code = str(row.get(code_col, "")).strip()
                industry = str(row.get(industry_col, "")).strip()
                if code and industry:
                    industry_lookup[code] = industry

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("snapshot CSV has no header")
        mapping = {k: find_field(reader.fieldnames, k) for k in ALIASES}
        for required in ("code", "pct_change", "amount"):
            if not mapping[required]:
                raise ValueError(f"missing required column for {required}; accepted aliases: {ALIASES[required]}")

        rows: list[dict[str, Any]] = []
        dropped = 0
        source_rows = 0
        for raw in reader:
            source_rows += 1
            code = str(raw.get(mapping["code"] or "", "")).strip()
            pct = to_float(raw.get(mapping["pct_change"] or ""))
            amount = to_float(raw.get(mapping["amount"] or ""))
            if not code or pct is None or amount is None or amount <= 0:
                dropped += 1
                continue
            row: dict[str, Any] = {
                "code": code,
                "name": str(raw.get(mapping["name"] or "", "")).strip(),
                "pct_change": pct,
                "amount": amount,
            }
            for key in (
                "turnover_rate", "amplitude", "high", "low", "open", "close",
                "prev_close", "float_market_cap", "total_market_cap",
            ):
                col = mapping[key]
                row[key] = to_float(raw.get(col)) if col else None
            industry = str(raw.get(mapping["industry"] or "", "")).strip() if mapping["industry"] else ""
            if not industry:
                industry = industry_lookup.get(code, "")
            row["industry"] = industry
            if row["high"] is not None and row["low"] is not None and row["close"] is not None:
                spread = row["high"] - row["low"]
                if spread > 0:
                    row["clv"] = clamp((row["close"] - row["low"]) / spread, 0.0, 1.0)
                else:
                    row["clv"] = None
            else:
                row["clv"] = None
            rows.append(row)

    if len(rows) < 10:
        raise ValueError(f"only {len(rows)} active rows remain; at least 10 are required")
    return Snapshot(rows=rows, dropped_rows=dropped, source_rows=source_rows, columns=mapping)


def top_share(rows: list[dict[str, Any]], frac: float) -> float:
    total = sum(r["amount"] for r in rows)
    k = max(1, math.ceil(len(rows) * frac))
    ranked = sorted(rows, key=lambda r: r["amount"], reverse=True)[:k]
    return sum(r["amount"] for r in ranked) / total if total else 0.0


def aggregate_industries(rows: list[dict[str, Any]], total_amount: float) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("industry"):
            buckets[str(row["industry"])].append(row)
    result = []
    for industry, members in buckets.items():
        amount = sum(r["amount"] for r in members)
        result.append({
            "industry": industry,
            "names": len(members),
            "amount_share": amount / total_amount if total_amount else 0.0,
            "positive_share": sum(1 for r in members if r["pct_change"] > 0) / len(members),
            "amount_weighted_return": weighted_mean(members, "pct_change") or 0.0,
        })
    return sorted(result, key=lambda x: x["amount_share"], reverse=True)


def analyze(snapshot: Snapshot, index_return: float | None = None) -> dict[str, Any]:
    rows = snapshot.rows
    n = len(rows)
    total_amount = sum(r["amount"] for r in rows)
    positive = [r for r in rows if r["pct_change"] > 0]
    negative = [r for r in rows if r["pct_change"] < 0]
    flat = n - len(positive) - len(negative)
    pos_share = len(positive) / n
    neg_share = len(negative) / n
    amount_pos_share = sum(r["amount"] for r in positive) / total_amount
    median_ret = statistics.median(r["pct_change"] for r in rows)

    top1 = top_share(rows, 0.01)
    top5 = top_share(rows, 0.05)
    top10 = top_share(rows, 0.10)
    weights = [r["amount"] / total_amount for r in rows]
    hhi = sum(w * w for w in weights)
    hhi_norm = ((hhi - 1 / n) / (1 - 1 / n) * 100.0) if n > 1 else 100.0
    effective_names = 1.0 / hhi if hhi > 0 else 0.0
    effective_ratio = effective_names / n
    turnover_gini = gini([r["amount"] for r in rows])

    decile_n = max(1, math.ceil(n * 0.10))
    by_return = sorted(rows, key=lambda r: r["pct_change"], reverse=True)
    hot_rows = by_return[:decile_n]
    weak_rows = by_return[-decile_n:]
    hot_amount_share = sum(r["amount"] for r in hot_rows) / total_amount
    weak_amount_share = sum(r["amount"] for r in weak_rows) / total_amount
    hot_clv = weighted_mean(hot_rows, "clv")

    by_amount = sorted(rows, key=lambda r: r["amount"], reverse=True)
    leader_rows = by_amount[:decile_n]
    rest_rows = by_amount[decile_n:]
    leader_ret = weighted_mean(leader_rows, "pct_change") or 0.0
    rest_ret = statistics.median(r["pct_change"] for r in rest_rows) if rest_rows else median_ret
    leadership_spread = leader_ret - rest_ret

    abs5_share = sum(1 for r in rows if abs(r["pct_change"]) >= 5.0) / n
    tr_values = [r["turnover_rate"] for r in rows if r.get("turnover_rate") is not None]
    high_turn_share = None
    high_turn_amount_share = None
    if tr_values:
        high_turn = [r for r in rows if r.get("turnover_rate") is not None and r["turnover_rate"] >= 10.0]
        high_turn_share = len(high_turn) / len(tr_values)
        high_turn_amount_share = sum(r["amount"] for r in high_turn) / total_amount
    amp_values = [r["amplitude"] for r in rows if r.get("amplitude") is not None]
    median_amplitude = statistics.median(amp_values) if amp_values else None

    float_caps = [r for r in rows if r.get("float_market_cap") is not None and r["float_market_cap"] > 0]
    smallcap_amount_share = None
    if len(float_caps) >= 20:
        cap_sorted = sorted(float_caps, key=lambda r: r["float_market_cap"])
        cutoff_n = max(1, math.ceil(len(cap_sorted) * 0.30))
        smallcap_amount_share = sum(r["amount"] for r in cap_sorted[:cutoff_n]) / total_amount

    concentration_top = scale_up(top10, 0.28, 0.55)
    concentration_gini = scale_up(turnover_gini, 0.55, 0.82)
    concentration_score = 0.60 * concentration_top + 0.40 * concentration_gini

    breadth_component = scale_up(pos_share, 0.35, 0.65)
    capital_component = scale_up(amount_pos_share, 0.35, 0.65)
    alignment_component = 100.0 - scale_up(abs(amount_pos_share - pos_share), 0.05, 0.20)
    participation_score = 0.45 * breadth_component + 0.35 * capital_component + 0.20 * alignment_component

    effective_component = scale_up(effective_ratio, 0.20, 0.55)
    liquidity_distribution_score = 100.0 - (0.70 * concentration_score + 0.30 * (100.0 - effective_component))

    spec_components = [
        scale_up(abs5_share, 0.03, 0.20),
        scale_up(hot_amount_share, 0.10, 0.30),
    ]
    if high_turn_share is not None:
        spec_components.append(scale_up(high_turn_share, 0.05, 0.30))
    if median_amplitude is not None:
        spec_components.append(scale_up(median_amplitude, 2.0, 6.0))
    speculation_score = sum(spec_components) / len(spec_components)

    divergence_component = scale_up(abs(amount_pos_share - pos_share), 0.08, 0.25)
    leader_component = scale_up(abs(leadership_spread), 1.5, 6.0)
    effective_fragility = 100.0 - scale_up(effective_ratio, 0.20, 0.50)
    fade_component = 0.0 if hot_clv is None else scale_up(0.55 - hot_clv, 0.0, 0.30)
    fragility_score = (
        0.30 * concentration_score
        + 0.25 * divergence_component
        + 0.20 * leader_component
        + 0.15 * effective_fragility
        + 0.10 * fade_component
    )

    risk_flags: list[str] = []
    constructive_signals: list[str] = []
    if concentration_score >= 70 or top10 >= 0.45:
        risk_flags.append("turnover-concentration")
    if abs(amount_pos_share - pos_share) >= 0.15:
        risk_flags.append("capital-breadth-divergence")
    if index_return is not None and index_return > 0.30 and pos_share < 0.45:
        risk_flags.append("index-up-breadth-weak")
    if leadership_spread >= 2.5 and top10 >= 0.40:
        risk_flags.append("leader-dependence")
    if speculation_score >= 75:
        risk_flags.append("speculative-crowding")
    if hot_clv is not None and hot_clv < 0.45 and statistics.mean(r["pct_change"] for r in hot_rows) > 0:
        risk_flags.append("leader-intraday-fade")
    if pos_share < 0.35 and amount_pos_share < 0.35:
        risk_flags.append("broad-risk-off")
    if weak_amount_share >= 0.24 and neg_share >= 0.55:
        risk_flags.append("selloff-liquidity-cluster")

    if pos_share >= 0.60 and amount_pos_share >= 0.60:
        constructive_signals.append("broad-participation")
    if top10 < 0.35 and effective_ratio >= 0.45:
        constructive_signals.append("distributed-liquidity")
    if abs(amount_pos_share - pos_share) < 0.08:
        constructive_signals.append("capital-breadth-alignment")
    if hot_clv is not None and hot_clv >= 0.70:
        constructive_signals.append("leader-close-confirmation")

    if participation_score >= 65 and fragility_score < 45 and speculation_score < 75:
        state = "broad-participation"
    elif speculation_score >= 70 and fragility_score >= 55:
        state = "speculative-crowding"
    elif participation_score < 35 and fragility_score >= 60:
        state = "deleveraging-stress"
    elif participation_score < 40:
        state = "defensive-contraction"
    elif fragility_score >= 55 or (index_return is not None and index_return > 0.30 and pos_share < 0.45):
        state = "narrow-leadership"
    else:
        state = "balanced-rotation"

    top_turnover_names = []
    for r in by_amount[:10]:
        top_turnover_names.append({
            "code": r["code"],
            "name": r.get("name") or "",
            "pct_change": round(r["pct_change"], 3),
            "amount_share": round(r["amount"] / total_amount, 6),
            "turnover_rate": r.get("turnover_rate"),
        })

    industries = aggregate_industries(rows, total_amount)

    return {
        "coverage": {
            "source_rows": snapshot.source_rows,
            "active_rows": n,
            "dropped_rows": snapshot.dropped_rows,
            "total_amount": total_amount,
        },
        "breadth": {
            "advancers": len(positive),
            "decliners": len(negative),
            "flat": flat,
            "positive_share": pos_share,
            "negative_share": neg_share,
            "amount_positive_share": amount_pos_share,
            "median_return_pct": median_ret,
            "abs5_name_share": abs5_share,
        },
        "liquidity_distribution": {
            "top1_turnover_share": top1,
            "top5_turnover_share": top5,
            "top10_turnover_share": top10,
            "turnover_hhi": hhi,
            "normalized_hhi_score": hhi_norm,
            "turnover_gini": turnover_gini,
            "effective_names": effective_names,
            "effective_names_ratio": effective_ratio,
        },
        "crowding": {
            "hot_return_decile_amount_share": hot_amount_share,
            "weak_return_decile_amount_share": weak_amount_share,
            "high_turnover_name_share": high_turn_share,
            "high_turnover_amount_share": high_turn_amount_share,
            "median_amplitude_pct": median_amplitude,
            "smallcap_amount_share": smallcap_amount_share,
            "leader_turnover_weighted_return_pct": leader_ret,
            "rest_median_return_pct": rest_ret,
            "leadership_spread_pct": leadership_spread,
            "hot_decile_close_location": hot_clv,
        },
        "scores": {
            "participation_score": round(clamp(participation_score), 2),
            "liquidity_distribution_score": round(clamp(liquidity_distribution_score), 2),
            "speculation_score": round(clamp(speculation_score), 2),
            "fragility_score": round(clamp(fragility_score), 2),
        },
        "state": state,
        "risk_flags": risk_flags,
        "constructive_signals": constructive_signals,
        "index_return_pct": index_return,
        "top_turnover_names": top_turnover_names,
        "industries": industries[:12],
    }


def load_history(path: Path | None, current_date: str) -> tuple[list[dict[str, Any]], dict[str, list[float]]]:
    if path is None or not path.exists():
        return [], {k: [] for k in KEY_HISTORY_FIELDS}
    rows: list[dict[str, Any]] = []
    values = {k: [] for k in KEY_HISTORY_FIELDS}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if str(row.get("date", "")).strip() == current_date:
                continue
            rows.append(row)
            for key in KEY_HISTORY_FIELDS:
                v = to_float(row.get(key))
                if v is not None:
                    values[key].append(v)
    return rows, values


def history_row(report_date: str, result: dict[str, Any]) -> dict[str, Any]:
    scores = result["scores"]
    breadth = result["breadth"]
    liq = result["liquidity_distribution"]
    return {
        "date": report_date,
        "participation_score": scores["participation_score"],
        "liquidity_distribution_score": scores["liquidity_distribution_score"],
        "speculation_score": scores["speculation_score"],
        "fragility_score": scores["fragility_score"],
        "positive_share": round(breadth["positive_share"], 6),
        "amount_positive_share": round(breadth["amount_positive_share"], 6),
        "top10_turnover_share": round(liq["top10_turnover_share"], 6),
        "turnover_gini": round(liq["turnover_gini"], 6),
        "state": result["state"],
    }


def add_history_context(result: dict[str, Any], history_values: dict[str, list[float]]) -> None:
    current = history_row("", result)
    percentiles: dict[str, float | None] = {}
    for key in KEY_HISTORY_FIELDS:
        val = to_float(current.get(key))
        percentiles[key] = None if val is None else pct_rank(val, history_values.get(key, []))
    result["history_context"] = {
        "prior_sessions": max((len(v) for v in history_values.values()), default=0),
        "percentile_rank": percentiles,
    }


def append_history(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: list[dict[str, Any]] = []
    if path.exists():
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            existing = list(csv.DictReader(f))
    existing = [r for r in existing if str(r.get("date", "")).strip() != row["date"]]
    existing.append({k: row.get(k, "") for k in ["date", *KEY_HISTORY_FIELDS, "state"]})
    existing.sort(key=lambda r: str(r.get("date", "")))
    with path.open("w", encoding="utf-8", newline="") as f:
        fields = ["date", *KEY_HISTORY_FIELDS, "state"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(existing)


def fmt_pct(ratio: float | None, digits: int = 1) -> str:
    if ratio is None:
        return "n/a"
    return f"{ratio * 100:.{digits}f}%"


def fmt_num(value: float | None, digits: int = 1) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def render_markdown(report_date: str, result: dict[str, Any]) -> str:
    c = result["coverage"]
    b = result["breadth"]
    l = result["liquidity_distribution"]
    cr = result["crowding"]
    s = result["scores"]
    history = result.get("history_context", {})
    pcts = history.get("percentile_rank", {}) if isinstance(history, dict) else {}

    lines = [
        f"# A-share Market Participation Report — {report_date}",
        "",
        f"**State:** `{result['state']}`",
        "",
        "## Scorecard",
        "",
        "| Metric | Score | Historical percentile |",
        "|---|---:|---:|",
    ]
    for key, label in (
        ("participation_score", "Participation"),
        ("liquidity_distribution_score", "Liquidity distribution"),
        ("speculation_score", "Speculation"),
        ("fragility_score", "Fragility risk"),
    ):
        pr = pcts.get(key)
        pr_text = "n/a" if pr is None else f"{pr:.0f}th"
        lines.append(f"| {label} | {s[key]:.1f} | {pr_text} |")

    lines.extend([
        "",
        "## Participation structure",
        "",
        f"- Active names: **{c['active_rows']}** / source rows {c['source_rows']} (dropped {c['dropped_rows']}).",
        f"- Advancers: **{fmt_pct(b['positive_share'])}**; decliners: **{fmt_pct(b['negative_share'])}**.",
        f"- Turnover in advancers: **{fmt_pct(b['amount_positive_share'])}**.",
        f"- Median stock return: **{b['median_return_pct']:.2f}%**; names with |return| ≥ 5%: **{fmt_pct(b['abs5_name_share'])}**.",
        "",
        "## Liquidity concentration",
        "",
        f"- Top 1% / 5% / 10% turnover share: **{fmt_pct(l['top1_turnover_share'])} / {fmt_pct(l['top5_turnover_share'])} / {fmt_pct(l['top10_turnover_share'])}**.",
        f"- Turnover Gini: **{l['turnover_gini']:.3f}**; effective traded names: **{l['effective_names']:.0f}** ({fmt_pct(l['effective_names_ratio'])} of active names).",
        "",
        "## Crowding and leadership",
        "",
        f"- Top return decile turnover share: **{fmt_pct(cr['hot_return_decile_amount_share'])}**; bottom return decile: **{fmt_pct(cr['weak_return_decile_amount_share'])}**.",
        f"- Top-turnover decile weighted return: **{cr['leader_turnover_weighted_return_pct']:.2f}%** vs rest median **{cr['rest_median_return_pct']:.2f}%** (spread **{cr['leadership_spread_pct']:.2f}pp**).",
        f"- High-turnover (≥10%) name share: **{fmt_pct(cr['high_turnover_name_share'])}**; median amplitude: **{fmt_num(cr['median_amplitude_pct'])}%**.",
        f"- Hot-decile close-location value: **{fmt_num(cr['hot_decile_close_location'], 2)}** (1.0 = closes at session high).",
        "",
        "## Flags",
        "",
    ])
    if result["risk_flags"]:
        lines.append("**Risk flags:** " + ", ".join(f"`{x}`" for x in result["risk_flags"]) + ".")
    else:
        lines.append("**Risk flags:** none triggered by the deterministic thresholds.")
    if result["constructive_signals"]:
        lines.append("\n**Constructive signals:** " + ", ".join(f"`{x}`" for x in result["constructive_signals"]) + ".")

    lines.extend([
        "",
        "## Highest-turnover names",
        "",
        "| Code | Name | Return | Turnover share | Turnover rate |",
        "|---|---|---:|---:|---:|",
    ])
    for row in result["top_turnover_names"]:
        tr = "n/a" if row["turnover_rate"] is None else f"{row['turnover_rate']:.2f}%"
        lines.append(f"| {row['code']} | {row['name']} | {row['pct_change']:.2f}% | {row['amount_share']*100:.2f}% | {tr} |")

    if result["industries"]:
        lines.extend([
            "",
            "## Industry participation (when supplied)",
            "",
            "| Industry | Turnover share | Advancer share | Amount-weighted return |",
            "|---|---:|---:|---:|",
        ])
        for row in result["industries"][:8]:
            lines.append(
                f"| {row['industry']} | {row['amount_share']*100:.1f}% | {row['positive_share']*100:.1f}% | {row['amount_weighted_return']:.2f}% |"
            )

    lines.extend([
        "",
        "## Interpretation guardrails",
        "",
        "- Treat these scores as descriptive market-state heuristics, not return forecasts or trading instructions.",
        "- Compare a session with its own historical distribution when possible; a single cross-section has limited context.",
        "- For post-close review, use a snapshot captured after the market close. Intraday snapshots are provisional.",
    ])
    return "\n".join(lines) + "\n"


def load_meta(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze A-share participation, liquidity concentration, and crowding.")
    parser.add_argument("snapshot", type=Path, help="CSV snapshot with code, pct_change, and amount columns")
    parser.add_argument("--date", dest="report_date", default=None, help="Report date, e.g. 2026-08-07")
    parser.add_argument("--index-return", type=float, default=None, help="Benchmark index return in percent, e.g. 0.82")
    parser.add_argument("--meta", type=Path, default=None, help="Optional JSON metadata from fetch_akshare_snapshot.py")
    parser.add_argument("--industry-map", type=Path, default=None, help="Optional CSV with code and industry columns")
    parser.add_argument("--history", type=Path, default=None, help="Optional historical metrics CSV for percentile context")
    parser.add_argument("--append-history", action="store_true", help="Append/replace current metrics in --history")
    parser.add_argument("--out-json", type=Path, default=None, help="Write structured JSON report")
    parser.add_argument("--out-md", type=Path, default=None, help="Write Markdown report")
    args = parser.parse_args()

    meta = load_meta(args.meta)
    report_date = args.report_date or str(meta.get("date") or date_cls.today().isoformat())
    index_return = args.index_return
    if index_return is None:
        index_return = to_float(meta.get("benchmark_pct_change"))

    snapshot = load_snapshot(args.snapshot, args.industry_map)
    result = analyze(snapshot, index_return=index_return)
    _, history_values = load_history(args.history, report_date)
    add_history_context(result, history_values)
    result["date"] = report_date
    if meta:
        result["source_meta"] = meta

    markdown = render_markdown(report_date, result)

    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.out_md:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        args.out_md.write_text(markdown, encoding="utf-8")
    if not args.out_md:
        print(markdown, end="")

    if args.append_history:
        if args.history is None:
            parser.error("--append-history requires --history")
        append_history(args.history, history_row(report_date, result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
