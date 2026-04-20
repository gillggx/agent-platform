#!/usr/bin/env python3
"""
Migration: add `anonymous_id` column to `users` table.

Safe to run multiple times — checks if column exists before altering.
Works on SQLite (primary target) and PostgreSQL.

Usage:
    cd backend
    .venv/bin/python migrations/add_anonymous_id.py
"""
import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings


async def column_exists(conn, table: str, column: str) -> bool:
    if "sqlite" in settings.database_url:
        result = await conn.execute(text(f"PRAGMA table_info({table})"))
        return any(row[1] == column for row in result.fetchall())
    # PostgreSQL
    result = await conn.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :table AND column_name = :column"
        ),
        {"table": table, "column": column},
    )
    return result.scalar() is not None


async def run():
    engine = create_async_engine(settings.database_url)
    try:
        async with engine.begin() as conn:
            if await column_exists(conn, "users", "anonymous_id"):
                print("✓ Column users.anonymous_id already exists — nothing to do.")
                return

            print("Adding column users.anonymous_id (VARCHAR(36))...")
            await conn.execute(
                text("ALTER TABLE users ADD COLUMN anonymous_id VARCHAR(36)")
            )

            # Create index for fast lookups — SQLite 支援 IF NOT EXISTS
            print("Creating index ix_users_anonymous_id...")
            await conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_anonymous_id "
                    "ON users(anonymous_id)"
                )
            )
            print("✓ Migration complete.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
