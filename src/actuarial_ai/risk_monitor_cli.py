"""Local scheduled ingestion of risk snapshots; no external notifications."""
import argparse
import json
import smtplib
import time
from pathlib import Path

from .alert_notifications import send_critical_alerts
from .risk_monitor import save_monitoring_run
from .risk_recalculation import calculate_monitoring_snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description="Persist Mack risk monitoring snapshots")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--snapshot", type=Path, help="Existing JSON snapshot")
    source.add_argument("--portfolio", type=Path, help="Portfolio triangles CSV")
    parser.add_argument(
        "--config", type=Path, help="JSON monitoring assumptions for --portfolio",
    )
    parser.add_argument("--database", type=Path, default=Path("mack_monitoring.sqlite3"))
    parser.add_argument(
        "--interval-seconds", type=int, default=0,
        help="Poll snapshot file at this interval (0 = run once)",
    )
    parser.add_argument(
        "--email-critical", action="store_true",
        help="Send critical alerts using configured SMTP environment variables",
    )
    args = parser.parse_args()
    if args.config is not None and args.portfolio is None:
        parser.error("--config requires --portfolio")
    if args.interval_seconds < 0:
        parser.error("--interval-seconds must be nonnegative")
    while True:
        try:
            if args.portfolio is not None:
                settings = (
                    json.loads(args.config.read_text(encoding="utf-8"))
                    if args.config is not None else {}
                )
                snapshot = calculate_monitoring_snapshot(
                    args.portfolio, **settings,
                )
            else:
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
                if args.email_critical:
                    try:
                        count = send_critical_alerts(
                            result["alerts"], run_id=result["run_id"],
                        )
                        if count:
                            print(f"Email sent for {count} critical alerts", flush=True)
                    except (OSError, ValueError, smtplib.SMTPException) as exc:
                        print(f"Email delivery failed: {exc}", flush=True)
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
