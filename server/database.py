"""
SQLite 데이터베이스 (라이센스 저장)
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, Tuple, List

DB_PATH = os.environ.get("DB_PATH", "/opt/license_server/licenses.db")


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS licenses (
                key          TEXT PRIMARY KEY,
                email        TEXT DEFAULT '',
                machine_id   TEXT DEFAULT '',
                activated_at TEXT DEFAULT '',
                expires_at   TEXT DEFAULT '9999-12-31',
                active       INTEGER DEFAULT 1,
                memo         TEXT DEFAULT '',
                created_at   TEXT DEFAULT ''
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS agreements (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                version      TEXT    NOT NULL,
                machine_id   TEXT    NOT NULL,
                hostname     TEXT    DEFAULT '',
                os_info      TEXT    DEFAULT '',
                client_ip    TEXT    DEFAULT '',
                agreed_at    TEXT    NOT NULL,
                created_at   TEXT    NOT NULL
            )
        """)
        c.commit()


def insert_license(key: str, email: str = "",
                   expires_at: str = "9999-12-31", memo: str = ""):
    with _conn() as c:
        c.execute(
            "INSERT INTO licenses (key, email, expires_at, memo, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (key, email, expires_at, memo,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        c.commit()


def get_license(key: str) -> Optional[dict]:
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM licenses WHERE key = ?", (key,)
        ).fetchone()
        return dict(row) if row else None


def bind_machine(key: str, machine_id: str):
    with _conn() as c:
        c.execute(
            "UPDATE licenses SET machine_id=?, activated_at=? WHERE key=?",
            (machine_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), key)
        )
        c.commit()


def revoke_license(key: str):
    with _conn() as c:
        c.execute("UPDATE licenses SET active=0 WHERE key=?", (key,))
        c.commit()


def get_license_by_email(email: str) -> Optional[dict]:
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM licenses WHERE email = ? ORDER BY created_at DESC LIMIT 1",
            (email.strip().lower(),)
        ).fetchone()
        return dict(row) if row else None


def insert_agreement(version: str, machine_id: str,
                     hostname: str, os_info: str, client_ip: str,
                     agreed_at: str) -> int:
    """동의 기록 저장 → 삽입된 row id 반환"""
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO agreements "
            "(version, machine_id, hostname, os_info, client_ip, agreed_at, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (version, machine_id, hostname, os_info, client_ip,
             agreed_at, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        c.commit()
        return cur.lastrowid


def list_agreements(page: int = 1, per_page: int = 50) -> Tuple[int, List[dict]]:
    offset = (page - 1) * per_page
    with _conn() as c:
        total = c.execute("SELECT COUNT(*) FROM agreements").fetchone()[0]
        rows  = c.execute(
            "SELECT * FROM agreements ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (per_page, offset)
        ).fetchall()
        return total, [dict(r) for r in rows]


def list_licenses(page: int = 1, per_page: int = 50) -> Tuple[int, List[dict]]:
    offset = (page - 1) * per_page
    with _conn() as c:
        total = c.execute("SELECT COUNT(*) FROM licenses").fetchone()[0]
        rows  = c.execute(
            "SELECT * FROM licenses ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (per_page, offset)
        ).fetchall()
        return total, [dict(r) for r in rows]
