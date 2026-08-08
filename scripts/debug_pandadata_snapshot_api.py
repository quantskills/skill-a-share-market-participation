#!/usr/bin/env python3
"""Probe the PandaData snapshot APIs used by the live fetcher."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_env_files() -> None:
    for candidate in (ROOT / ".env", ROOT / ".env.local"):
        if not candidate.exists():
            continue
        try:
            text = candidate.read_text(encoding="utf-8-sig")
        except OSError:
            continue
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def _service_root() -> str:
    base = (
        os.getenv("PANDA_DATA_BASE_URL")
        or os.getenv("JAVA_SERVICE_BASE_URL")
        or os.getenv("HTTP_SERVICE_BASE_URL")
        or "http://pandadata.pandaaiquant.com"
    )
    base = base.rstrip("/")
    if base.endswith("/pandaData"):
        base = base[: -len("/pandaData")]
    return base


def _fmt_exc(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Show which PandaData snapshot API fails.")
    parser.add_argument("--exchange", default="SH", help="Exchange for trade-date probe")
    parser.add_argument("--trade-date", default=None, help="Override trade date, default = latest trade date")
    args = parser.parse_args()

    _load_env_files()

    username = os.getenv("PANDA_DATA_USERNAME") or os.getenv("DEFAULT_USERNAME") or ""
    password = os.getenv("PANDA_DATA_PASSWORD") or os.getenv("DEFAULT_PASSWORD") or ""
    if not username or not password:
        raise SystemExit("missing credentials: set PANDA_DATA_USERNAME / PANDA_DATA_PASSWORD")

    try:
        import panda_data
    except Exception as exc:
        raise SystemExit(f"import failed: {_fmt_exc(exc)}") from exc

    base_url = _service_root()
    print(f"base_url={base_url}")

    try:
        panda_data.init_token(username=username, password=password, base_url=base_url)
        print("login_ok=true")
    except Exception as exc:
        raise SystemExit(f"login_failed: {_fmt_exc(exc)}") from exc

    try:
        latest = panda_data.get_last_trade_date(exchange=args.exchange)
        print(f"latest_trade_date={latest}")
    except Exception as exc:
        print(f"latest_trade_date_failed: {_fmt_exc(exc)}")
        latest = args.trade_date or "20260807"

    probes = [
        ("get_stock_daily", {"symbol": [], "start_date": latest, "end_date": latest, "fields": ["symbol", "date", "name", "close", "pre_close", "volume", "amount"]}),
    ]

    for method_name, kwargs in probes:
        print(f"\n== {method_name} ==")
        print(f"args={kwargs}")
        try:
            df = getattr(panda_data, method_name)(**kwargs)
            print(f"ok rows={len(df)} cols={list(df.columns)}")
            if not df.empty:
                print(df.head(2).to_dict("records"))
        except Exception as exc:
            print(f"error={_fmt_exc(exc)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
