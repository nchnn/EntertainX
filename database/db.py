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
            role          TEXT    NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
            created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id         INTEGER PRIMARY KEY REFERENCES users(id),
            primary_color   TEXT    NOT NULL DEFAULT '#6C63FF',
            secondary_color TEXT    NOT NULL DEFAULT '#FF6584',
            updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS remember_tokens (
            selector   TEXT    PRIMARY KEY,
            user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token_hash BLOB    NOT NULL,
            created_at TEXT    NOT NULL DEFAULT (datetime('now')),
            expires_at TEXT    NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_remember_tokens_user
            ON remember_tokens (user_id);
    """)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
    if "role" not in columns:
        conn.execute(
            "ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user' "
            "CHECK (role IN ('user', 'admin'))"
        )
    conn.commit()
