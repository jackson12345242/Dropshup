import os
import aiosqlite
import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS products(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  supplier_cost REAL NOT NULL,
  selling_price REAL NOT NULL,
  url TEXT NOT NULL,
  shipping_cost REAL NOT NULL DEFAULT 0,
  other_expenses REAL NOT NULL DEFAULT 0,
  added_by INTEGER,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS orders(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id INTEGER NOT NULL REFERENCES products(id),
  quantity INTEGER NOT NULL DEFAULT 1,
  sale_price REAL NOT NULL,
  est_profit REAL NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  simulated INTEGER NOT NULL DEFAULT 1,
  actual_profit REAL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""


def connect():
    return aiosqlite.connect(config.DB_PATH)


async def init():
    d = os.path.dirname(config.DB_PATH)
    if d:
        os.makedirs(d, exist_ok=True)
    async with connect() as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.executescript(SCHEMA)
        await db.commit()


async def fetch(sql: str, args=()):
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(sql, args) as cur:
            return await cur.fetchall()


async def execute(sql: str, args=()) -> int:
    async with connect() as db:
        cur = await db.execute(sql, args)
        await db.commit()
        return cur.lastrowid


async def get_setting(key: str, default: str = "") -> str:
    rows = await fetch("SELECT value FROM settings WHERE key=?", (key,))
    return rows[0]["value"] if rows else default


async def set_setting(key: str, value: str):
    await execute("INSERT INTO settings(key,value) VALUES(?,?) "
                  "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
