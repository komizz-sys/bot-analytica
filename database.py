import aiosqlite
import config

CREATE_EXPENSES_TABLE = """
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount_uzs INTEGER NOT NULL,
    description TEXT,
    added_by INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);
"""


async def init_db():
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute(CREATE_EXPENSES_TABLE)
        await db.commit()


async def add_expense(amount_uzs: int, description: str, added_by: int) -> int:
    async with aiosqlite.connect(config.DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO expenses (amount_uzs, description, added_by) VALUES (?, ?, ?)",
            (amount_uzs, description, added_by),
        )
        await db.commit()
        return cur.lastrowid


async def get_expenses_sum(since_sql: str | None) -> int:
    query = "SELECT COALESCE(SUM(amount_uzs), 0) FROM expenses"
    params: list = []
    if since_sql:
        query += " WHERE created_at >= ?"
        params.append(since_sql)
    async with aiosqlite.connect(config.DB_PATH) as db:
        async with db.execute(query, params) as cur:
            return (await cur.fetchone())[0]


async def get_recent_expenses(limit: int = 10) -> list[dict]:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM expenses ORDER BY id DESC LIMIT ?", (limit,)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def delete_expense(expense_id: int) -> bool:
    async with aiosqlite.connect(config.DB_PATH) as db:
        cur = await db.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        await db.commit()
        return cur.rowcount > 0
