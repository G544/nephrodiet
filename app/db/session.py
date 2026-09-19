from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import get_settings

settings = get_settings()

# pre_ping/recycle: Neon suspends idle compute and drops idle pooled connections.
engine = create_async_engine(
    settings.async_database_url,
    connect_args=settings.async_connect_args,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False,
)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)
