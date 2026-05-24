"""数据存储 - SQLite账号管理"""

import sqlite3
import os
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "accounts.db")


def get_db() -> sqlite3.Connection:
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """初始化数据库表"""
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            stoken TEXT NOT NULL,
            uid TEXT NOT NULL,
            mid TEXT DEFAULT '',
            server TEXT DEFAULT '官服',
            note TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)
    conn.commit()
    conn.close()


def add_account(name: str, stoken: str, uid: str, mid: str = "",
                server: str = "官服", note: str = "") -> dict:
    """添加账号"""
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO accounts (name, stoken, uid, mid, server, note) VALUES (?, ?, ?, ?, ?, ?)",
        (name, stoken, uid, mid, server, note)
    )
    conn.commit()
    account_id = cursor.lastrowid
    conn.close()
    return get_account(account_id)


def get_account(account_id: int) -> Optional[dict]:
    """获取单个账号"""
    conn = get_db()
    row = conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def get_all_accounts() -> list[dict]:
    """获取所有账号"""
    conn = get_db()
    rows = conn.execute("SELECT * FROM accounts ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_account(account_id: int, **kwargs) -> Optional[dict]:
    """更新账号信息"""
    if not kwargs:
        return get_account(account_id)
    
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values())
    values.append(account_id)
    
    conn = get_db()
    conn.execute(f"UPDATE accounts SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()
    return get_account(account_id)


def delete_account(account_id: int) -> bool:
    """删除账号"""
    conn = get_db()
    cursor = conn.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


def find_account_by_uid(uid: str) -> Optional[dict]:
    """通过UID查找账号"""
    conn = get_db()
    row = conn.execute("SELECT * FROM accounts WHERE uid = ?", (uid,)).fetchone()
    conn.close()
    return dict(row) if row else None
