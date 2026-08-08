#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

import pandas as pd

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import fetch_akshare_snapshot as fetcher


class FakePandaData:
    def __init__(self, frame: pd.DataFrame | None = None, fail: bool = False) -> None:
        self.frame = frame
        self.fail = fail
        self.calls: list[str] = []
        self.init_kwargs: dict[str, str] | None = None

    def init_token(self, **kwargs) -> None:
        self.calls.append("init_token")
        self.init_kwargs = kwargs

    def get_stock_rt_daily(self, **kwargs) -> pd.DataFrame:
        self.calls.append("get_stock_rt_daily")
        if self.fail:
            raise RuntimeError("boom")
        return self.frame if self.frame is not None else pd.DataFrame()

    def get_stock_daily_post(self, **kwargs) -> pd.DataFrame:
        self.calls.append("get_stock_daily_post")
        return self.frame if self.frame is not None else pd.DataFrame()

    def get_stock_daily(self, **kwargs) -> pd.DataFrame:
        self.calls.append("get_stock_daily")
        return self.frame if self.frame is not None else pd.DataFrame()


class FakeAkShare:
    def __init__(self, frame: pd.DataFrame) -> None:
        self.frame = frame
        self.calls: list[str] = []

    def stock_zh_a_spot_em(self) -> pd.DataFrame:
        self.calls.append("stock_zh_a_spot_em")
        return self.frame


class FetchSnapshotTests(unittest.TestCase):
    def test_pandadata_is_primary(self) -> None:
        panda = FakePandaData(
            pd.DataFrame(
                [
                    {"symbol": "600000", "name": "浦发银行", "close": 12.34, "pre_close": 12.00, "volume": 10.0, "turnover_rate": 2.5},
                    {"symbol": "600001", "name": "邯郸钢铁", "close": 8.80, "pre_close": 9.00, "volume": 5.0, "turnover_rate": 1.2},
                ]
            )
        )
        ak = FakeAkShare(pd.DataFrame([{"代码": "000001", "名称": "平安银行", "涨跌幅": 2.0, "成交额": 10.0}]))

        frame, meta = fetcher.fetch_snapshot(panda_sdk=panda, akshare_sdk=ak)

        self.assertEqual(["init_token", "get_stock_daily"], panda.calls)
        self.assertEqual("PandaData", meta["primary_source"])
        self.assertNotIn("fallback_source", meta)
        self.assertEqual(["600000", "600001"], frame["code"].tolist())
        self.assertIn("amount", frame.columns)
        self.assertAlmostEqual(2.833333333333333, float(frame.iloc[0]["pct_change"]))
        self.assertAlmostEqual(123.4, float(frame.iloc[0]["amount"]))

    def test_akshare_fallback(self) -> None:
        panda = FakePandaData(fail=True)
        ak = FakeAkShare(
            pd.DataFrame(
                [
                    {"代码": "000001", "名称": "平安银行", "涨跌幅": 2.0, "成交额": 10.0, "换手率": 1.1},
                    {"代码": "000002", "名称": "万科A", "涨跌幅": -1.5, "成交额": 8.0, "换手率": 0.8},
                ]
            )
        )

        frame, meta = fetcher.fetch_snapshot(panda_sdk=panda, akshare_sdk=ak)

        self.assertEqual(
            ["init_token", "get_stock_daily"],
            panda.calls,
        )
        self.assertEqual(["stock_zh_a_spot_em"], ak.calls)
        self.assertEqual("AKShare", meta["fallback_source"])
        self.assertIn("primary_error", meta)
        self.assertEqual(["000001", "000002"], frame["code"].tolist())
        self.assertAlmostEqual(2.0, float(frame.iloc[0]["pct_change"]))

    def test_dotenv_is_loaded_for_auto_login(self) -> None:
        panda = FakePandaData(
            pd.DataFrame(
                [
                    {"symbol": "600000", "name": "浦发银行", "pct_change": 1.2, "money": 123.4},
                ]
            )
        )
        with unittest.mock.patch.dict("os.environ", {}, clear=True):
            with tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                (root / ".env").write_text(
                    "PANDA_DATA_USERNAME=dotenv_user\nPANDA_DATA_PASSWORD=dotenv_pass\n",
                    encoding="utf-8",
                )
                with patch.object(fetcher.Path, "cwd", return_value=root):
                    frame, _ = fetcher.fetch_snapshot(panda_sdk=panda, akshare_sdk=FakeAkShare(pd.DataFrame()))

        self.assertEqual(["600000"], frame["code"].tolist())
        self.assertEqual({"username": "dotenv_user", "password": "dotenv_pass"}, panda.init_kwargs)


if __name__ == "__main__":
    unittest.main()
