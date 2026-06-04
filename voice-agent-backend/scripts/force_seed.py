"""
One-off: wipe and reseed the database the app is configured to use.

Drops every table, recreates the schema, and runs the clinic demo seed. Point it at
the target DB via the same DATABASE_URL the app uses (e.g. Railway's), then run:

    python -m scripts.force_seed

Prefer the FORCE_SEED=true env var on Railway startup for the normal case; this script
is for running manually against a DB from a shell / Railway console.
"""
import asyncio

from app.db.database import engine, reset_schema
from app.db.seed import seed_mock_data


async def force():
    # reset_schema() drops + recreates the whole public schema, clearing orphan tables
    # from the old restaurant schema that a model-only drop_all can't remove.
    await reset_schema()
    print("[force_seed] schema dropped + recreated")
    await seed_mock_data()
    await engine.dispose()
    print("[force_seed] Force seed complete")


if __name__ == "__main__":
    asyncio.run(force())
