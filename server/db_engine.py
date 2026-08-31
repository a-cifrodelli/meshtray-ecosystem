from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from models import Base  # ORM già definito altrove
import config as c

# ===== Database ORM =====
engine: AsyncEngine = create_async_engine(c.DATABASE_URL, echo=True)
db_session_factory = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

import os

async def init_db():
    # Assicura che la cartella genitrice del database esista prima dell'inizializzazione
    if hasattr(c, "DATABASE_PATH") and c.DATABASE_PATH:
        db_dir = os.path.dirname(os.path.abspath(c.DATABASE_PATH))
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
