"""
Migration: Add token_expires_at, label, and scopes columns to oauth_accounts.

Run this once after updating the OAuthAccount model.
Safe to run multiple times — checks for column existence first.

Usage:
    python -m jarvis.database.migrate_oauth_columns
"""
import asyncio
import structlog
from sqlalchemy import text
from jarvis.database.core import engine

logger = structlog.get_logger(__name__)

MIGRATIONS = [
    ("token_expires_at", "ALTER TABLE oauth_accounts ADD COLUMN token_expires_at DATETIME"),
    ("label", "ALTER TABLE oauth_accounts ADD COLUMN label VARCHAR(50)"),
    ("scopes", "ALTER TABLE oauth_accounts ADD COLUMN scopes VARCHAR"),
]


async def migrate():
    async with engine.begin() as conn:
        # Check which columns already exist
        result = await conn.execute(text("PRAGMA table_info(oauth_accounts)"))
        existing_columns = {row[1] for row in result.fetchall()}

        for col_name, sql in MIGRATIONS:
            if col_name in existing_columns:
                logger.info("migration.skip", column=col_name, reason="already exists")
            else:
                await conn.execute(text(sql))
                logger.info("migration.added", column=col_name)

    logger.info("migration.complete")


if __name__ == "__main__":
    asyncio.run(migrate())
