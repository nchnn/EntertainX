import sqlite3


def get_connection(db_path: str = "entertainx.db") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    UNIQUE NOT NULL,
            email         TEXT    UNIQUE NOT NULL COLLATE NOCASE,
            password_hash BLOB    NOT NULL,
            salt          BLOB    NOT NULL,
            created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id         INTEGER PRIMARY KEY REFERENCES users(id),
            primary_color   TEXT    NOT NULL DEFAULT '#6C63FF',
            secondary_color TEXT    NOT NULL DEFAULT '#FF6584',
            updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
