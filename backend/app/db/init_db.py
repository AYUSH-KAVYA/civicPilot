"""
Database initialization script for CivicPilot.
Creates pgvector extensions, generates all tables from SQLAlchemy models,
and runs the seed script.
"""

import asyncio

# Ensure all models are imported so Base.metadata knows about them
import backend.app.db.models  # noqa: F401
from backend.app.db.seed import seed_database
from backend.app.db.session import AsyncSessionLocal, Base, engine, init_db_extensions


async def init_all() -> None:
    print("[Init DB] Initializing extensions...")
    await init_db_extensions()

    print("[Init DB] Creating tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("[Init DB] Running seed data...")
    async with AsyncSessionLocal() as session:
        await seed_database(session)

    print("[Init DB] Initialization complete!")


if __name__ == "__main__":
    asyncio.run(init_all())
