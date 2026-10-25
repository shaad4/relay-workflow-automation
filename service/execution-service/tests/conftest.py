"""Keep database integration tests independent across asyncio event loops."""

from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from app.db.database import DATABASE_URL, engine


database = make_url(DATABASE_URL)
if database.database == "ci_test" and database.host in {"localhost", "127.0.0.1"}:
    # Several tests create their own event loop with asyncio.run(). A pooled
    # asyncpg connection cannot be reused by a later test's event loop.
    engine.sync_engine.pool = NullPool(engine.sync_engine.pool._creator)
