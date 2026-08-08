#!/usr/bin/env python3
"""Fetch a canonical A-share market snapshot with PandaData first and AKShare fallback."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

SNAPSHOT_ALIASES: dict[str, tuple[str, ...]] = {
    "code": ("code", "symbol", "代码", "证券代码"),
    "name": ("name", "名称", "证券简称"),
    "pct_change": ("pct_change", "pct_chg", "chg_pct", "change_pct", "涨跌幅", "涨幅"),
    "amount": ("amount", "money", "turnover", "turnover_amount", "成交额", "金额"),
    "turnover_rate": ("turnover_rate", "换手率", "换手"),
    "amplitude": ("amplitude", "振幅"),
    "high": ("high", "最高"),
    "low": ("low", "最低"),
    "open": ("open", "今开"),
    "close": ("close", "最新价", "收盘"),
    "prev_close": ("prev_close", "pre_close", "昨收", "前收盘"),
    "volume": ("volume", "成交量", "vol"),
    "float_market_cap": ("float_market_cap", "流通市值"),
    "total_market_cap": ("total_market_cap", "总市值"),
}


def _find_column(headers: list[str], aliases: tuple[str, ...]) -> str | None:
    header_map = {str(header).strip(): str(header) for header in headers if header is not None}
    for alias in aliases:
        if alias in header_map:
            return header_map[alias]
    return None


def _stringify(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip()
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    return text


def _to_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
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
    if not pd.isna(result):
        return float(result)
    return None


def _normalise_snapshot_frame(frame: pd.DataFrame, *, exclude_st: bool = False) -> pd.DataFrame:
    mapping = {key: _find_column(list(frame.columns), aliases) for key, aliases in SNAPSHOT_ALIASES.items()}
    missing = [key for key in ("code",) if not mapping[key]]
    if missing:
        raise ValueError(f"snapshot frame is missing required columns: {', '.join(missing)}")

    result = pd.DataFrame()
    result["code"] = frame[mapping["code"]].map(_stringify)
    result["name"] = frame[mapping["name"]].map(_stringify) if mapping["name"] else ""
    result["pct_change"] = frame[mapping["pct_change"]].map(_to_float) if mapping["pct_change"] else pd.Series([None] * len(frame), index=frame.index)
    result["amount"] = frame[mapping["amount"]].map(_to_float) if mapping["amount"] else pd.Series([None] * len(frame), index=frame.index)

    for key in (
        "turnover_rate",
        "amplitude",
        "high",
        "low",
        "open",
        "close",
        "prev_close",
        "volume",
        "float_market_cap",
        "total_market_cap",
    ):
        result[key] = frame[mapping[key]].map(_to_float) if mapping[key] else None

    if result["pct_change"].isna().any() and result["close"].notna().any() and result["prev_close"].notna().any():
        mask = result["pct_change"].isna() & result["close"].notna() & result["prev_close"].notna() & (result["prev_close"] != 0)
        result.loc[mask, "pct_change"] = (result.loc[mask, "close"] - result.loc[mask, "prev_close"]) / result.loc[mask, "prev_close"] * 100.0

    if result["amount"].isna().any() and result["volume"].notna().any() and result["close"].notna().any():
        mask = result["amount"].isna() & result["volume"].notna() & result["close"].notna()
        result.loc[mask, "amount"] = result.loc[mask, "volume"] * result.loc[mask, "close"]

    if result["amount"].isna().any() and result["volume"].notna().any() and result["prev_close"].notna().any():
        mask = result["amount"].isna() & result["volume"].notna() & result["prev_close"].notna()
        result.loc[mask, "amount"] = result.loc[mask, "volume"] * result.loc[mask, "prev_close"]

    result = result.dropna(subset=["code", "pct_change", "amount"])
    result = result[result["code"].astype(str).str.strip() != ""]
    result = result[result["amount"] > 0]
    if exclude_st and mapping["name"]:
        result = result[~frame[mapping["name"]].astype(str).str.upper().str.contains("ST", na=False)]

    return result.reset_index(drop=True)


def _skill_root() -> Path | None:
    for parent in Path(__file__).resolve().parents:
        if (parent / "SKILL.md").exists():
            return parent
    return None


def _parse_dotenv(path: Path) -> dict[str, str]:
    if not path.exists() or not path.is_file():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[key] = value
    return values


def _load_dotenv_files() -> None:
    candidates = [Path.cwd() / ".env"]
    skill_root = _skill_root()
    if skill_root is not None:
        candidates.append(skill_root / ".env")
    seen: set[Path] = set()
    for path in candidates:
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        for key, value in _parse_dotenv(resolved).items():
            os.environ.setdefault(key, value)


class PandaDataSnapshotSource:
    def __init__(
        self,
        *,
        sdk: Any | None = None,
        auto_login: bool = False,
        username_env: str = "PANDA_DATA_USERNAME",
        password_env: str = "PANDA_DATA_PASSWORD",
        base_url_env: str | None = "PANDA_DATA_BASE_URL",
    ) -> None:
        self._sdk = sdk
        self.auto_login = auto_login
        self.username_env = username_env
        self.password_env = password_env
        self.base_url_env = base_url_env
        self._authenticated = False

    def _client(self) -> Any:
        _load_dotenv_files()
        if self._sdk is None:
            self._sdk = importlib.import_module("panda_data")
        if self.auto_login and not self._authenticated and hasattr(self._sdk, "init_token"):
            username = self._first_env_value(self.username_env, "PANDA_DATA_USERNAME", "DEFAULT_USERNAME")
            password = self._first_env_value(self.password_env, "PANDA_DATA_PASSWORD", "DEFAULT_PASSWORD")
            if not username or not password:
                raise RuntimeError(
                    f"PandaData auto_login requires {self.username_env} and {self.password_env}"
                )
            kwargs: dict[str, str] = {"username": username, "password": password}
            if self.base_url_env:
                base_url = self._first_env_value(self.base_url_env, "PANDA_DATA_BASE_URL", "DEFAULT_BASE_URL")
                if base_url:
                    kwargs["base_url"] = base_url
            self._sdk.init_token(**kwargs)
            self._authenticated = True
        return self._sdk

    @staticmethod
    def _first_env_value(*names: str | None) -> str:
        for name in names:
            if not name:
                continue
            value = os.getenv(name, "").strip()
            if value:
                return value
        return ""

    def fetch(self, exclude_st: bool = False) -> tuple[pd.DataFrame, dict[str, Any]]:
        client = self._client()
        trade_date = self._latest_trade_date(client)
        method_name = "get_stock_daily"
        if not hasattr(client, method_name):
            raise RuntimeError("PandaData client does not expose get_stock_daily")
        last_error: Exception | None = None
        raw = None
        for attempt in range(3):
            try:
                raw = getattr(client, method_name)(
                    symbol=[],
                    start_date=trade_date,
                    end_date=trade_date,
                    fields=["symbol", "date", "name", "close", "pre_close", "volume", "amount"],
                )
                last_error = None
                break
            except Exception as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(1 << attempt)
        if last_error is not None:
            raise RuntimeError(f"PandaData {method_name} failed: {type(last_error).__name__}: {last_error}") from last_error
        if raw is None or raw.empty:
            raise RuntimeError("PandaData get_stock_daily returned no rows")
        frame = _normalise_snapshot_frame(raw, exclude_st=exclude_st)
        if frame.empty:
            raise RuntimeError("PandaData get_stock_daily returned no usable A-share snapshot")
        return frame, {"data_source": f"PandaData {method_name}", "trade_date": trade_date}

    @staticmethod
    def _latest_trade_date(client: Any) -> str:
        try:
            if hasattr(client, "get_last_trade_date"):
                value = client.get_last_trade_date(exchange="SH")
                if value:
                    return str(value)
        except Exception:
            pass
        return datetime.now().strftime("%Y%m%d")


class AkShareSnapshotSource:
    def __init__(self, *, sdk: Any | None = None) -> None:
        self._sdk = sdk

    def _client(self) -> Any:
        if self._sdk is None:
            self._sdk = importlib.import_module("akshare")
        return self._sdk

    def fetch(self, exclude_st: bool = False) -> tuple[pd.DataFrame, dict[str, Any]]:
        client = self._client()
        raw = client.stock_zh_a_spot_em()
        if raw is None or raw.empty:
            raise RuntimeError("AKShare returned no usable A-share snapshot")
        frame = _normalise_snapshot_frame(raw, exclude_st=exclude_st)
        return frame, {"data_source": "AKShare stock_zh_a_spot_em (Eastmoney)"}


def _fetch_benchmark_pct_change(benchmark: str) -> tuple[float | None, str | None]:
    try:
        ak = importlib.import_module("akshare")
        idx = ak.stock_zh_index_spot_em(symbol="沪深重要指数")
        if idx is None or idx.empty:
            return None, None
        if "名称" not in idx.columns or "涨跌幅" not in idx.columns:
            return None, None
        hit = idx[idx["名称"].astype(str) == benchmark]
        if hit.empty:
            return None, None
        value = hit.iloc[0]["涨跌幅"]
        return float(value), "AKShare stock_zh_index_spot_em"
    except Exception:
        return None, None


def fetch_snapshot(
    *,
    exclude_st: bool = False,
    auto_login: bool = True,
    username_env: str = "PANDA_DATA_USERNAME",
    password_env: str = "PANDA_DATA_PASSWORD",
    base_url_env: str | None = "PANDA_DATA_BASE_URL",
    panda_sdk: Any | None = None,
    akshare_sdk: Any | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    panda = PandaDataSnapshotSource(
        sdk=panda_sdk,
        auto_login=auto_login,
        username_env=username_env,
        password_env=password_env,
        base_url_env=base_url_env,
    )
    try:
        frame, meta = panda.fetch(exclude_st=exclude_st)
        meta["primary_source"] = "PandaData"
        return frame, meta
    except Exception as primary_error:
        akshare = AkShareSnapshotSource(sdk=akshare_sdk)
        frame, meta = akshare.fetch(exclude_st=exclude_st)
        meta["primary_source"] = "PandaData"
        meta["fallback_source"] = "AKShare"
        meta["primary_error"] = f"{type(primary_error).__name__}: {primary_error}"
        return frame, meta


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch A-share spot data with PandaData first and AKShare fallback."
    )
    parser.add_argument("--out", type=Path, required=True, help="Destination CSV path")
    parser.add_argument("--meta-out", type=Path, default=None, help="Optional metadata JSON path")
    parser.add_argument("--benchmark", default="沪深300", help="Benchmark index name for metadata")
    parser.add_argument("--exclude-st", action="store_true", help="Exclude names containing ST or *ST")
    parser.add_argument(
        "--pandadata-auto-login",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Call panda_data.init_token from env vars",
    )
    parser.add_argument("--pandadata-username-env", default="PANDA_DATA_USERNAME")
    parser.add_argument("--pandadata-password-env", default="PANDA_DATA_PASSWORD")
    parser.add_argument("--pandadata-base-url-env", default="PANDA_DATA_BASE_URL")
    args = parser.parse_args()

    out, meta = fetch_snapshot(
        exclude_st=args.exclude_st,
        auto_login=args.pandadata_auto_login,
        username_env=args.pandadata_username_env,
        password_env=args.pandadata_password_env,
        base_url_env=args.pandadata_base_url_env,
    )

    out = out.copy()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False, encoding="utf-8-sig")

    now = datetime.now().astimezone()
    benchmark_pct_change, benchmark_source = _fetch_benchmark_pct_change(args.benchmark)
    meta.update(
        {
            "date": meta.get("trade_date") or now.date().isoformat(),
            "fetched_at": now.isoformat(),
            "benchmark": args.benchmark,
            "benchmark_pct_change": benchmark_pct_change,
            "benchmark_source": benchmark_source,
            "rows": int(len(out)),
        }
    )

    meta_path = args.meta_out or args.out.with_suffix(".meta.json")
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(out)} rows to {args.out}")
    print(f"wrote metadata to {meta_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
