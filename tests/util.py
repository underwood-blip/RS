import json
from pathlib import Path

FIX = Path(__file__).resolve().parent / "fixtures"


def make_snapshot():
    rows = json.loads((FIX / "stocks_rows.json").read_text(encoding="utf-8"))
    return {
        "fetched_at": "2026-09-23T13:43:00+00:00",
        "home": {
            "cross": [
                {"symbol": "LB:SMH.US", "name": "半導體", "score": 1.4, "d1": 0.1, "d5": 10.1,
                 "d20": 10.6, "d60": -8.4, "rankDelta5d": 23, "rsLine": [1, 1.1]},
                {"symbol": "LB:GLD.US", "name": "黃金", "score": -0.5, "d1": -0.7, "d5": 0.1,
                 "d20": -5.8, "d60": 6.5, "rankDelta5d": -4, "rsLine": [1, 0.99]},
            ],
            "macro": [
                {"symbol": "SPY.US", "name": "S&P 500", "price": 772.28, "d1": -0.14, "d5": 2.67},
            ],
            "pulse": {
                "counts": [{"label": "突然走強", "n": 1, "tone": "up"}],
                "groups": [{"title": "突然走強", "count": 1, "items": [
                    {"key": "美股-LB:WDAY.US", "ticker": "WDAY", "name": "Workday,",
                     "rank": 72, "move": "↑284", "excess": "+1.2%", "hero": None, "streak": None}]}],
            },
        },
        "tabs": {"stocks": {"tab": "stocks", "label": "美股", "rows": rows, "fetched_at": "d"}},
        "errors": {},
    }
