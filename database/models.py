"""
SQLAlchemy ORM modellari.

Tuzatilgan muammolar:
  - Channel modeli async_main() dan keyin edi → jadval yaratilmaydi (kritik bug). Endi to'g'rilandi.
  - Tez-tez so'raladigan ustunlarga Index qo'shildi.
  - Connection pool sozlamalari qo'shildi.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func

from config.config import DB_URL
from utils.logger import get_logger

logger = get_logger(__name__)

# ── Engine va session fabrikasi ───────────────────────────────────────────────
engine = create_async_engine(
    DB_URL,
    echo=False,
    pool_size=10,          # Bir vaqtda ochiq ulanmalar soni
    max_overflow=20,       # Pool to'lsa qo'shimcha ulanmalar
    pool_timeout=30,       # Ulanma kutish vaqti (soniya)
    pool_recycle=1800,     # 30 daqiqada bir ulanmani yangilash
    pool_pre_ping=True,    # Har so'rovda ulanma tirikligini tekshirish
)

async_session = async_sessionmaker(engine, expire_on_commit=False)


# ── Base ──────────────────────────────────────────────────────────────────────
class Base(AsyncAttrs, DeclarativeBase):
    pass


# ── Modellar ──────────────────────────────────────────────────────────────────
class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(primary_key=True)
    kino_kodi: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    likes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dislikes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_movies_kino_kodi", "kino_kodi"),  # Qidiruv tezligi uchun
    )

    def __repr__(self) -> str:
        return f"<Movie kino_kodi={self.kino_kodi!r} message_id={self.message_id}>"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    referred_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_users_telegram_id", "telegram_id"),
    )

    def __repr__(self) -> str:
        return f"<User telegram_id={self.telegram_id} full_name={self.full_name!r}>"


class Vote(Base):
    """Foydalanuvchi ovozi. Bir foydalanuvchi bir kinoga faqat bir marta ovoz bera oladi."""
    __tablename__ = "votes"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    kino_kodi: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(10), nullable=False)

    __table_args__ = (
        UniqueConstraint("telegram_id", "kino_kodi", name="uq_vote_user_movie"),
    )


class Favorite(Base):
    """Foydalanuvchi sevimli kinolari."""
    __tablename__ = "favorites"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    kino_kodi: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("telegram_id", "kino_kodi", name="uq_favorite_user_movie"),
    )


class MissedSearch(Base):
    """So'ralgan, lekin bazada topilmagan kino kodlari (admin uchun talab signali)."""
    __tablename__ = "missed_searches"

    id: Mapped[int] = mapped_column(primary_key=True)
    kino_kodi: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    last_requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Channel(Base):
    """Majburiy obuna kanallari."""
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(primary_key=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    link: Mapped[str] = mapped_column(String(512), nullable=False)

    __table_args__ = (
        Index("ix_channels_channel_id", "channel_id"),
    )

    def __repr__(self) -> str:
        return f"<Channel channel_id={self.channel_id} title={self.title!r}>"


# ── Jadval yaratish ───────────────────────────────────────────────────────────
async def async_main() -> None:
    """Barcha jadvallarni (agar mavjud bo'lmasa) yaratadi."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # ponytail: qo'lda ALTER TABLE — mavjud jadvallarga yangi ustun qo'shish uchun
        # (create_all buni qilmaydi). Sxema tez-tez o'zgarsa Alembic'ga o'tish kerak.
        await conn.execute(text(
            "ALTER TABLE movies ADD COLUMN IF NOT EXISTS created_at "
            "TIMESTAMPTZ NOT NULL DEFAULT now()"
        ))
        await conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS referred_by BIGINT"
        ))
    logger.info("Ma'lumotlar bazasi jadvallari tayyor.")
