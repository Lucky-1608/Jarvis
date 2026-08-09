import asyncio

from sqlalchemy import text

from jarvis.database.core import Base, engine


async def init_models():
    async with engine.begin() as conn:
        print("Creating tables...")
        # Enable pgvector if using Postgres
        if str(engine.url).startswith("postgresql"):
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

        await conn.run_sync(Base.metadata.create_all)
        print("Tables created successfully!")

if __name__ == "__main__":
    asyncio.run(init_models())
