#!/usr/bin/env python3
from __future__ import annotations

import csv
import tempfile
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import analyze_market_participation as analyzer


class AnalyzerTests(unittest.TestCase):
    def write_snapshot(self, rows):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".csv", newline="", encoding="utf-8", delete=False)
        with tmp:
            writer = csv.DictWriter(tmp, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        return Path(tmp.name)

    def test_broad_participation_scores_higher_than_narrow_rally(self):
        broad = []
        narrow = []
        for i in range(100):
            broad.append({
                "code": f"B{i:03d}", "name": f"B{i}",
                "pct_change": 1.5 if i < 68 else -0.6,
                "amount": 100 + (i % 10) * 2,
                "turnover_rate": 4 + (i % 4), "amplitude": 3.0,
                "high": 10.5, "low": 9.8, "close": 10.4,
            })
            narrow.append({
                "code": f"N{i:03d}", "name": f"N{i}",
                "pct_change": 7.0 if i < 8 else (-1.2 if i < 70 else 0.2),
                "amount": 1800 if i < 8 else 40 + (i % 5),
                "turnover_rate": 18 if i < 8 else 2, "amplitude": 7 if i < 8 else 2.5,
                "high": 11.0, "low": 9.5, "close": 10.0 if i < 8 else 9.8,
            })
        broad_result = analyzer.analyze(analyzer.load_snapshot(self.write_snapshot(broad)), index_return=1.0)
        narrow_result = analyzer.analyze(analyzer.load_snapshot(self.write_snapshot(narrow)), index_return=1.0)
        self.assertGreater(broad_result["scores"]["participation_score"], narrow_result["scores"]["participation_score"])
        self.assertLess(broad_result["scores"]["fragility_score"], narrow_result["scores"]["fragility_score"])
        self.assertIn("turnover-concentration", narrow_result["risk_flags"])
        self.assertIn("index-up-breadth-weak", narrow_result["risk_flags"])

    def test_requires_minimum_columns(self):
        path = self.write_snapshot([{"code": str(i), "pct_change": i} for i in range(12)])
        with self.assertRaises(ValueError):
            analyzer.load_snapshot(path)


if __name__ == "__main__":
    unittest.main()
