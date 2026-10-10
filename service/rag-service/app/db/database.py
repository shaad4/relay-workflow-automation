import os

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
)

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
)