import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not configured")


engine_options = {
    "pool_pre_ping": True,
}

# Celery creates a new asyncio event loop for each task.
# Disable connection pooling only for Celery workers.
if os.getenv("CELERY_WORKER") == "true":
    engine_options["poolclass"] = NullPool


engine = create_async_engine(
    DATABASE_URL,
    **engine_options,
)


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass
