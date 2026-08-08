#!/usr/bin/env python3
"""Minimal PandaData login probe."""

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


def main() -> int:
    parser = argparse.ArgumentParser(description="Test PandaData login and a tiny probe request.")
    parser.add_argument("--exchange", default="SH", help="Exchange code for get_last_trade_date")
    args = parser.parse_args()

    _load_env_files()

    username = os.getenv("PANDA_DATA_USERNAME") or os.getenv("DEFAULT_USERNAME") or ""
    password = os.getenv("PANDA_DATA_PASSWORD") or os.getenv("DEFAULT_PASSWORD") or ""
    if not username or not password:
        raise SystemExit("missing credentials: set PANDA_DATA_USERNAME / PANDA_DATA_PASSWORD in .env")

    try:
        import panda_data
    except Exception as exc:
        raise SystemExit(f"import failed: {type(exc).__name__}: {exc}") from exc

    base_url = _service_root()
    print(f"base_url={base_url}")

    try:
        panda_data.init_token(username=username, password=password)
        print("login_ok=true")
    except Exception as exc:
        raise SystemExit(f"login_failed: {type(exc).__name__}: {exc}") from exc

    try:
        latest = panda_data.get_last_trade_date(exchange=args.exchange)
        print(f"latest_trade_date={latest}")
    except Exception as exc:
        raise SystemExit(f"probe_failed: {type(exc).__name__}: {exc}") from exc

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
