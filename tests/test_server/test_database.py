import pytest
from models import Message
import db_engine as db
from sqlalchemy import select

@pytest.mark.asyncio
async def test_database_lifecycle():
    # 1. Inizializza le tabelle del database in memoria
    await db.init_db()

    # 2. Inserisce un messaggio di prova
    async with db.db_session_factory() as session:
        msg = Message(
            sender="node_A",
            dest="node_B",
            text="Hello Mesh!",
            channel="default",
            seen=False
        )
        session.add(msg)
        await session.commit()

    # 3. Recupera e verifica il messaggio dal database
    async with db.db_session_factory() as session:
        stmt = select(Message).where(Message.sender == "node_A")
        result = await session.execute(stmt)
        msg_db = result.scalars().first()
        
        assert msg_db is not None
        assert msg_db.text == "Hello Mesh!"
        assert msg_db.dest == "node_B"
        assert msg_db.channel == "default"
        assert msg_db.seen is False
