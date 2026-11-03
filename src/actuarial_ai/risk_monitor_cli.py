"""Local scheduled ingestion of risk snapshots; no external notifications."""
import argparse
import json
import time
from pathlib import Path

from .risk_monitor import save_monitoring_run


def main() -> None:
    parser = argparse.ArgumentParser(description="Persist Mack risk monitoring snapshots")
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--database", type=Path, default=Path("mack_monitoring.sqlite3"))
    parser.add_argument(
        "--interval-seconds", type=int, default=0,
        help="Poll snapshot file at this interval (0 = run once)",
    )
    args = parser.parse_args()
    if args.interval_seconds < 0:
        parser.error("--interval-seconds must be nonnegative")
    while True:
        try:
            snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
            result = save_monitoring_run(args.database, snapshot)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            print(f"Monitoring failed: {exc}", flush=True)
            if args.interval_seconds == 0:
                raise SystemExit(1) from exc
        else:
            if result["created"]:
                print(
                    f"Run {result['run_id']}: {len(result['alerts'])} new alerts",
                    flush=True,
                )
                for alert in result["alerts"]:
                    print(
                        f"ALERT {alert['scope']}/{alert['name']}: "
                        f"{alert['previous_status']} -> {alert['status']}",
                        flush=True,
                    )
        if args.interval_seconds == 0:
            break
        time.sleep(args.interval_seconds)


if __name__ == "__main__":
    main()
