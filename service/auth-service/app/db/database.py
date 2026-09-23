from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = "postgresql+asyncpg://relay:relay@localhost:5432/relay_auth"

engine = create_async_engine(
    DATABASE_URL,
    echo=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)