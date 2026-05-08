from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy import BigInteger, String, Integer, DateTime
from sqlalchemy.sql import func 
from config.config import DB_URL

engine = create_async_engine(DB_URL, echo=False)
async_session = async_sessionmaker(engine)

class Base(AsyncAttrs, DeclarativeBase):
    pass

class Movie(Base):
    __tablename__ = 'movies'
    id: Mapped[int] = mapped_column(primary_key=True)
    kino_kodi: Mapped[str] = mapped_column(String, unique=True)
    message_id: Mapped[int] = mapped_column(BigInteger)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    dislikes: Mapped[int] = mapped_column(Integer, default=0)

# --- YANGI JADVAL: FOYDALANUVCHILAR ---
class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    full_name: Mapped[str] = mapped_column(String)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
class Channel(Base):
    __tablename__ = 'channels'
    id: Mapped[int] = mapped_column(primary_key=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, unique=True) 
    title: Mapped[str] = mapped_column(String) 
    link: Mapped[str] = mapped_column(String)  