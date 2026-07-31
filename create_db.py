import asyncio
from jarvis.database.core import engine, Base
from jarvis.database.models import User, Project, APIKey, AuditLog, OAuthAccount

async def init_models():
    async with engine.begin() as conn:
        print("Creating tables...")
        await conn.run_sync(Base.metadata.create_all)
        print("Tables created successfully!")

if __name__ == "__main__":
    asyncio.run(init_models())
