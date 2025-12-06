"""Simple CLI wrapper for the WB P&L service."""

from __future__ import annotations

import argparse
import json
from datetime import datetime

from .service import build_pnl_from_wb


def _parse_date(value: str) -> datetime.date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute WB P&L snapshot via API token.")
    parser.add_argument("--token", required=True, help="WB API token")
    parser.add_argument("--date-from", type=_parse_date, help="Start date YYYY-MM-DD (default: 30 days ago)")
    parser.add_argument("--date-to", type=_parse_date, help="End date YYYY-MM-DD (default: today)")
    parser.add_argument("--limit", type=int, default=None, help="Max rows to fetch (WB default 200000)")
    args = parser.parse_args()

    result = build_pnl_from_wb(
        args.token,
        date_from=args.date_from,
        date_to=args.date_to,
        limit=args.limit,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
