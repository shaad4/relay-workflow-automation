import os

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import database_options, database_url

DATABASE_URL = database_url()


engine_options = database_options()

# Celery creates a new asyncio event loop for each task.
# Disable connection pooling only for Celery workers.
if os.getenv("CELERY_WORKER") == "true":
    engine_options = {
        "poolclass": NullPool,
        "echo": False,
        "hide_parameters": True,
        "pool_pre_ping": True,
    }


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
