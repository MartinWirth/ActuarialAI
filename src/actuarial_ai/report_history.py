"""Local SQLite report archive. Explicit saves only; no user authentication."""
import hashlib
import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .report_builder import ReportOptions


def _connect(db_path):
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_utc TEXT NOT NULL,
            version TEXT NOT NULL,
            source TEXT NOT NULL,
            input_sha256 TEXT NOT NULL,
            options_json TEXT NOT NULL,
            summary_json TEXT NOT NULL,
            governance_json TEXT,
            portfolio_csv BLOB NOT NULL,
            pdf BLOB NOT NULL
        )
    """)
    connection.commit()
    return connection


def save_report(
    db_path, *, version: str, source: str, portfolio_csv: bytes,
    pdf: bytes, options: ReportOptions, summary: dict,
    governance: dict | None = None,
) -> int:
    """Append an immutable report snapshot, including input CSV and PDF."""
    if not portfolio_csv or not pdf.startswith(b"%PDF"):
        raise ValueError("Valid input CSV and PDF are required")
    with _connect(db_path) as connection:
        cursor = connection.execute(
            """INSERT INTO reports
               (created_utc, version, source, input_sha256, options_json,
                summary_json, governance_json, portfolio_csv, pdf)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.now(timezone.utc).isoformat(), version, source,
                hashlib.sha256(portfolio_csv).hexdigest(),
                json.dumps(asdict(options), sort_keys=True),
                json.dumps(summary, sort_keys=True, allow_nan=False),
                json.dumps(governance, sort_keys=True, allow_nan=False)
                if governance is not None else None,
                portfolio_csv, pdf,
            ),
        )
        return cursor.lastrowid


def list_reports(db_path, limit: int = 100) -> list[dict]:
    """Return report metadata newest first, without loading binary blobs."""
    if not 1 <= limit <= 1000:
        raise ValueError("limit must be between 1 and 1000")
    with _connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """SELECT id, created_utc, version, source, input_sha256,
                      summary_json, governance_json
               FROM reports ORDER BY id DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    return [
        {
            "id": row["id"], "created_utc": row["created_utc"],
            "version": row["version"], "source": row["source"],
            "input_sha256": row["input_sha256"],
            "summary": json.loads(row["summary_json"]),
            "governance": json.loads(row["governance_json"])
            if row["governance_json"] else None,
        }
        for row in rows
    ]


def get_report(db_path, report_id: int) -> dict | None:
    """Retrieve a saved report and its original input bytes."""
    with _connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT * FROM reports WHERE id = ?", (report_id,),
        ).fetchone()
    if row is None:
        return None
    return {
        "id": row["id"], "created_utc": row["created_utc"],
        "version": row["version"], "source": row["source"],
        "input_sha256": row["input_sha256"],
        "options": json.loads(row["options_json"]),
        "summary": json.loads(row["summary_json"]),
        "governance": json.loads(row["governance_json"])
        if row["governance_json"] else None,
        "portfolio_csv": row["portfolio_csv"], "pdf": row["pdf"],
    }
