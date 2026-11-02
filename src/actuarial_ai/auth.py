"""Local authentication and role-based permissions for demonstration deployments."""
import hashlib
import hmac
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

from .report_history import _connect

ROLES = {"ADMIN", "ACTUARY", "REVIEWER", "AUDITOR"}
PERMISSIONS = {
    "ADMIN": {"manage_users", "read_reports", "save_reports", "submit_review"},
    "ACTUARY": {"read_reports", "save_reports", "submit_review"},
    "REVIEWER": {"read_reports", "approve_reports"},
    "AUDITOR": {"read_reports"},
}


def _setup(connection):
    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY, role TEXT NOT NULL,
            salt BLOB NOT NULL, password_hash BLOB NOT NULL,
            active INTEGER NOT NULL DEFAULT 1
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS auth_sessions (
            token_hash TEXT PRIMARY KEY,
            username TEXT NOT NULL REFERENCES users(username),
            expires_utc TEXT NOT NULL
        )
    """)


def _hash_password(password, salt):
    return hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=16384, r=8, p=1,
    )


def create_user(db_path, username, password, role, *, admin_token=None):
    username = username.strip()
    if not username or len(username) > 80 or len(password) < 12:
        raise ValueError("Username required (max 80); password must be at least 12 characters")
    if role not in ROLES:
        raise ValueError("Invalid role")
    with _connect(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        _setup(connection)
        count = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if count:
            require_permission(db_path, admin_token, "manage_users")
        elif role != "ADMIN":
            raise PermissionError("First user must be ADMIN")
        salt = secrets.token_bytes(16)
        try:
            connection.execute(
                """INSERT INTO users (username, role, salt, password_hash)
                   VALUES (?, ?, ?, ?)""",
                (username, role, salt, _hash_password(password, salt)),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("Username already exists") from exc


def has_users(db_path):
    with _connect(db_path) as connection:
        _setup(connection)
        return bool(connection.execute("SELECT 1 FROM users LIMIT 1").fetchone())


def login(db_path, username, password):
    with _connect(db_path) as connection:
        _setup(connection)
        row = connection.execute(
            "SELECT salt, password_hash, active FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if row is None:
            _hash_password(password, b"0" * 16)
            raise PermissionError("Invalid credentials")
        if not row[2] or not hmac.compare_digest(
            _hash_password(password, row[0]), row[1],
        ):
            raise PermissionError("Invalid credentials")
        token = secrets.token_urlsafe(32)
        connection.execute(
            "INSERT INTO auth_sessions VALUES (?, ?, ?)",
            (
                hashlib.sha256(token.encode()).hexdigest(), username,
                (datetime.now(timezone.utc) + timedelta(hours=8)).isoformat(),
            ),
        )
    return token


def identity(db_path, token):
    if not token:
        return None
    digest = hashlib.sha256(token.encode()).hexdigest()
    with _connect(db_path) as connection:
        _setup(connection)
        row = connection.execute(
            """SELECT users.username, users.role, auth_sessions.expires_utc
               FROM auth_sessions JOIN users USING (username)
               WHERE token_hash = ? AND users.active = 1""",
            (digest,),
        ).fetchone()
    if row is None or datetime.fromisoformat(row[2]) <= datetime.now(timezone.utc):
        return None
    return {"username": row[0], "role": row[1]}


def require_permission(db_path, token, permission):
    user = identity(db_path, token)
    if user is None or permission not in PERMISSIONS[user["role"]]:
        raise PermissionError(f"Permission denied: {permission}")
    return user


def logout(db_path, token):
    if token:
        with _connect(db_path) as connection:
            _setup(connection)
            connection.execute(
                "DELETE FROM auth_sessions WHERE token_hash = ?",
                (hashlib.sha256(token.encode()).hexdigest(),),
            )


def list_users(db_path, admin_token):
    require_permission(db_path, admin_token, "manage_users")
    with _connect(db_path) as connection:
        return [
            {"username": username, "role": role, "active": bool(active)}
            for username, role, active in connection.execute(
                "SELECT username, role, active FROM users ORDER BY username",
            )
        ]
