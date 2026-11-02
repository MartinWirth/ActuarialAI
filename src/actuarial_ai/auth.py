"""Local authentication and role-based permissions for demonstration deployments."""
import hashlib
import hmac
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

from .report_history import _connect

MAX_FAILURES = 5
LOCK_MINUTES = 15
SESSION_HOURS = 8
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
            active INTEGER NOT NULL DEFAULT 1,
            failed_attempts INTEGER NOT NULL DEFAULT 0,
            locked_until TEXT
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS auth_sessions (
            token_hash TEXT PRIMARY KEY,
            username TEXT NOT NULL REFERENCES users(username),
            expires_utc TEXT NOT NULL
        )
    """)
    columns = {row[1] for row in connection.execute("PRAGMA table_info(users)")}
    if "failed_attempts" not in columns:
        connection.execute("ALTER TABLE users ADD COLUMN failed_attempts INTEGER NOT NULL DEFAULT 0")
    if "locked_until" not in columns:
        connection.execute("ALTER TABLE users ADD COLUMN locked_until TEXT")
    connection.execute("""
        CREATE TABLE IF NOT EXISTS security_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_utc TEXT NOT NULL,
            username TEXT NOT NULL,
            event TEXT NOT NULL
        )
    """)


def _event(connection, username, event):
    connection.execute(
        "INSERT INTO security_events (created_utc, username, event) VALUES (?, ?, ?)",
        (datetime.now(timezone.utc).isoformat(), username, event),
    )


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
    """Limit failures per account; unknown users receive a dummy hash check."""
    now = datetime.now(timezone.utc)
    with _connect(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        _setup(connection)
        row = connection.execute(
            """SELECT salt, password_hash, active, failed_attempts, locked_until
               FROM users WHERE username = ?""",
            (username,),
        ).fetchone()
        if row is None:
            _hash_password(password, b"0" * 16)
            raise PermissionError("Invalid credentials")
        if row[4] and datetime.fromisoformat(row[4]) > now:
            raise PermissionError("Invalid credentials")
        if not row[2] or not hmac.compare_digest(
            _hash_password(password, row[0]), row[1],
        ):
            attempts = row[3] + 1
            locked_until = (
                (now + timedelta(minutes=LOCK_MINUTES)).isoformat()
                if attempts >= MAX_FAILURES else None
            )
            connection.execute(
                """UPDATE users SET failed_attempts = ?, locked_until = ?
                   WHERE username = ?""",
                (attempts, locked_until, username),
            )
            _event(
                connection, username,
                "LOGIN_LOCKOUT" if locked_until else "LOGIN_FAILURE",
            )
            token = None
        else:
            connection.execute(
                """UPDATE users SET failed_attempts = 0, locked_until = NULL
                   WHERE username = ?""",
                (username,),
            )
            token = secrets.token_urlsafe(32)
            connection.execute(
                "INSERT INTO auth_sessions VALUES (?, ?, ?)",
                (
                    hashlib.sha256(token.encode()).hexdigest(), username,
                    (now + timedelta(hours=SESSION_HOURS)).isoformat(),
                ),
            )
            _event(connection, username, "LOGIN_SUCCESS")
    if token is None:
        raise PermissionError("Invalid credentials")
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


def change_password(db_path, token, old_password, new_password):
    user = require_permission(db_path, token, "read_reports")
    if len(new_password) < 12:
        raise ValueError("New password must be at least 12 characters")
    with _connect(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT salt, password_hash FROM users WHERE username = ?",
            (user["username"],),
        ).fetchone()
        if not hmac.compare_digest(_hash_password(old_password, row[0]), row[1]):
            raise PermissionError("Current password incorrect")
        salt = secrets.token_bytes(16)
        connection.execute(
            """UPDATE users SET salt = ?, password_hash = ?,
               failed_attempts = 0, locked_until = NULL WHERE username = ?""",
            (salt, _hash_password(new_password, salt), user["username"]),
        )
        connection.execute(
            "DELETE FROM auth_sessions WHERE username = ?", (user["username"],),
        )
        _event(connection, user["username"], "PASSWORD_CHANGED")


def set_user_active(db_path, admin_token, username, active):
    admin = require_permission(db_path, admin_token, "manage_users")
    if username == admin["username"] and not active:
        raise ValueError("Cannot deactivate own administrator account")
    with _connect(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT role, active FROM users WHERE username = ?", (username,),
        ).fetchone()
        if row is None:
            raise ValueError("Unknown user")
        if not active and row[0] == "ADMIN" and row[1]:
            count = connection.execute(
                "SELECT COUNT(*) FROM users WHERE role = 'ADMIN' AND active = 1",
            ).fetchone()[0]
            if count <= 1:
                raise ValueError("Cannot deactivate last administrator")
        connection.execute(
            """UPDATE users SET active = ?, failed_attempts = 0,
               locked_until = NULL WHERE username = ?""",
            (int(active), username),
        )
        if not active:
            connection.execute(
                "DELETE FROM auth_sessions WHERE username = ?", (username,),
            )
        _event(connection, username, "ACCOUNT_ENABLED" if active else "ACCOUNT_DISABLED")


def security_events(db_path, admin_token, limit=100):
    require_permission(db_path, admin_token, "manage_users")
    with _connect(db_path) as connection:
        _setup(connection)
        return [
            {"created_utc": created, "username": username, "event": event}
            for created, username, event in connection.execute(
                """SELECT created_utc, username, event FROM security_events
                   ORDER BY id DESC LIMIT ?""",
                (min(max(int(limit), 1), 1000),),
            )
        ]
