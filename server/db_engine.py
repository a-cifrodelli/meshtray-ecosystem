from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from models import Base  # ORM già definito altrove
import config as c

# ===== Database ORM =====
engine: AsyncEngine = create_async_engine(c.DATABASE_URL, echo=True)
db_session_factory = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
