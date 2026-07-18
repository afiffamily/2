"""
Ma'lumotlar bazasi so'rovlari (Data Access Layer).

Tuzatilgan muammolar:
  - print() → logging
  - rate_movie race condition → atomik UPDATE
  - add_user username field qo'shildi
  - Barcha funksiyalarda to'g'ri xato boshqaruvi
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from config.config import REFERRAL_THRESHOLD
from database.models import Channel, Favorite, MissedSearch, Movie, User, Vote, async_session
from utils.logger import get_logger

logger = get_logger(__name__)


# ── Kino operatsiyalari ───────────────────────────────────────────────────────
async def add_movie(kino_kodi: str, message_id: int) -> bool:
    """
    Yangi kino qo'shadi yoki mavjudini yangilaydi.
    True qaytaradi: yangi qo'shildi; False: mavjud, yangilandi.
    """
    kino_kodi = kino_kodi.strip()
    async with async_session() as session:
        async with session.begin():
            movie = await session.scalar(
                select(Movie).where(Movie.kino_kodi == kino_kodi)
            )
            if movie:
                movie.message_id = message_id
                logger.info("Kino yangilandi: kod=%s, message_id=%s", kino_kodi, message_id)
                return False
            else:
                session.add(Movie(kino_kodi=kino_kodi, message_id=message_id))
                logger.info("Yangi kino qo'shildi: kod=%s, message_id=%s", kino_kodi, message_id)
                return True


async def get_movie(kino_kodi: str) -> int | None:
    """Kino kodiga mos message_id qaytaradi, topilmasa None."""
    kino_kodi = kino_kodi.strip()
    async with async_session() as session:
        message_id = await session.scalar(
            select(Movie.message_id).where(Movie.kino_kodi == kino_kodi)
        )
        if message_id:
            logger.debug("Kino topildi: kod=%s, message_id=%s", kino_kodi, message_id)
        else:
            logger.debug("Kino topilmadi: kod=%s", kino_kodi)
        return message_id


async def rate_movie(kino_kodi: str, action: str, telegram_id: int) -> str:
    """
    Kinoga like/dislike beradi.
    Har foydalanuvchi bir kinoga faqat bir marta ovoz bera oladi (Vote jadvalidagi
    unique constraint orqali — race condition holatida ham xavfsiz).

    Qaytaradi: "ok" | "already_voted" | "not_found" | "invalid".
    """
    kino_kodi = kino_kodi.strip()
    if action not in ("like", "dislike"):
        logger.warning("Noto'g'ri rate action: %s", action)
        return "invalid"

    column = Movie.likes if action == "like" else Movie.dislikes
    async with async_session() as session:
        try:
            async with session.begin():
                movie_id = await session.scalar(
                    select(Movie.id).where(Movie.kino_kodi == kino_kodi)
                )
                if movie_id is None:
                    logger.warning("rate_movie: kino topilmadi, kod=%s", kino_kodi)
                    return "not_found"

                session.add(Vote(telegram_id=telegram_id, kino_kodi=kino_kodi, action=action))
                await session.flush()
                await session.execute(
                    update(Movie)
                    .where(Movie.id == movie_id)
                    .values({column.key: column + 1})
                )
        except IntegrityError:
            logger.debug("Takroriy ovoz: user_id=%s, kod=%s", telegram_id, kino_kodi)
            return "already_voted"

    logger.debug("Reyting yangilandi: kod=%s, action=%s, user_id=%s", kino_kodi, action, telegram_id)
    return "ok"


async def get_recent_movies(limit: int = 10) -> list[Movie]:
    """Oxirgi qo'shilgan kinolarni qaytaradi (katalog uchun)."""
    async with async_session() as session:
        result = await session.scalars(
            select(Movie).order_by(Movie.created_at.desc()).limit(limit)
        )
        return list(result.all())


async def delete_movie_by_code(kino_kodi: str) -> bool:
    """Kino kodiga mos kinoni bazadan o'chiradi."""
    kino_kodi = kino_kodi.strip()
    async with async_session() as session:
        async with session.begin():
            movie = await session.scalar(
                select(Movie).where(Movie.kino_kodi == kino_kodi)
            )
            if not movie:
                return False
            await session.delete(movie)
    logger.info("Kino o'chirildi: kod=%s", kino_kodi)
    return True


# ── Topilmagan qidiruvlar ─────────────────────────────────────────────────────
async def record_missed_search(kino_kodi: str) -> None:
    """Bazada topilmagan kino kodini qayd etadi (admin uchun talab signali)."""
    kino_kodi = kino_kodi.strip()
    async with async_session() as session:
        async with session.begin():
            missed = await session.scalar(
                select(MissedSearch).where(MissedSearch.kino_kodi == kino_kodi)
            )
            if missed:
                missed.count += 1
                missed.last_requested_at = datetime.now(timezone.utc)
            else:
                session.add(MissedSearch(kino_kodi=kino_kodi))


async def get_top_missed_searches(limit: int = 5) -> list[MissedSearch]:
    """Eng ko'p so'ralgan, lekin bazada topilmagan kodlarni qaytaradi."""
    async with async_session() as session:
        result = await session.scalars(
            select(MissedSearch).order_by(MissedSearch.count.desc()).limit(limit)
        )
        return list(result.all())


# ── Foydalanuvchi operatsiyalari ─────────────────────────────────────────────
async def add_user(
    telegram_id: int,
    full_name: str,
    username: str | None = None,
    referred_by: int | None = None,
) -> bool:
    """
    Yangi foydalanuvchini ro'yxatdan o'tkazadi.
    True: yangi; False: allaqachon mavjud.
    referred_by faqat yangi foydalanuvchi uchun va o'z-o'zini taklif qilish bo'lmasa saqlanadi.
    """
    if referred_by == telegram_id:
        referred_by = None

    async with async_session() as session:
        async with session.begin():
            exists = await session.scalar(
                select(User.id).where(User.telegram_id == telegram_id)
            )
            if exists:
                return False
            session.add(
                User(
                    telegram_id=telegram_id,
                    full_name=full_name,
                    username=username,
                    referred_by=referred_by,
                )
            )
    logger.info(
        "Yangi foydalanuvchi: id=%s, ism=%s, taklif_qilgan=%s",
        telegram_id, full_name, referred_by,
    )
    return True


async def get_new_users_count(days: int) -> int:
    """Oxirgi N kun ichida ro'yxatdan o'tgan foydalanuvchilar sonini qaytaradi."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    async with async_session() as session:
        return await session.scalar(
            select(func.count(User.id)).where(User.created_at >= since)
        ) or 0


async def get_referral_count(telegram_id: int) -> int:
    """Foydalanuvchi taklif qilgan (ro'yxatdan o'tgan) do'stlar sonini qaytaradi."""
    async with async_session() as session:
        return await session.scalar(
            select(func.count(User.id)).where(User.referred_by == telegram_id)
        ) or 0


async def is_referral_exempt(telegram_id: int) -> bool:
    """Foydalanuvchi yetarlicha do'st taklif qilib, majburiy obunadan ozod bo'lganmi."""
    count = await get_referral_count(telegram_id)
    return count >= REFERRAL_THRESHOLD


async def get_all_users() -> list[User]:
    """Barcha foydalanuvchilarni qaytaradi."""
    async with async_session() as session:
        result = await session.scalars(select(User))
        return list(result.all())


async def get_statistics() -> tuple[int, int, list[Movie]]:
    """(jami_users, jami_movies, top3_movies) qaytaradi."""
    async with async_session() as session:
        total_users = await session.scalar(select(func.count(User.id))) or 0
        total_movies = await session.scalar(select(func.count(Movie.id))) or 0
        top_movies = await session.scalars(
            select(Movie).order_by(Movie.likes.desc()).limit(3)
        )
        return total_users, total_movies, list(top_movies.all())


# ── Sevimlilar ─────────────────────────────────────────────────────────────────
async def toggle_favorite(telegram_id: int, kino_kodi: str) -> bool:
    """Sevimlilarga qo'shadi yoki olib tashlaydi. True: qo'shildi; False: olib tashlandi."""
    kino_kodi = kino_kodi.strip()
    async with async_session() as session:
        async with session.begin():
            favorite = await session.scalar(
                select(Favorite).where(
                    Favorite.telegram_id == telegram_id, Favorite.kino_kodi == kino_kodi
                )
            )
            if favorite:
                await session.delete(favorite)
                return False
            session.add(Favorite(telegram_id=telegram_id, kino_kodi=kino_kodi))
            return True


async def get_user_favorites(telegram_id: int) -> list[str]:
    """Foydalanuvchining sevimli kino kodlari ro'yxatini qaytaradi (eng yangisi birinchi)."""
    async with async_session() as session:
        result = await session.scalars(
            select(Favorite.kino_kodi)
            .where(Favorite.telegram_id == telegram_id)
            .order_by(Favorite.created_at.desc())
        )
        return list(result.all())


# ── Kanal operatsiyalari ─────────────────────────────────────────────────────
async def get_all_channels() -> list[Channel]:
    """Barcha majburiy obuna kanallarini qaytaradi."""
    async with async_session() as session:
        result = await session.scalars(select(Channel))
        return list(result.all())


async def add_channel(channel_id: int, title: str, link: str) -> bool:
    """Yangi kanal qo'shadi. True: qo'shildi; False: allaqachon bor."""
    async with async_session() as session:
        async with session.begin():
            exists = await session.scalar(
                select(Channel.id).where(Channel.channel_id == channel_id)
            )
            if exists:
                return False
            session.add(Channel(channel_id=channel_id, title=title, link=link))
    logger.info("Yangi kanal qo'shildi: id=%s, nom=%s", channel_id, title)
    return True


async def delete_channel(channel_id: int) -> bool:
    """Kanalni o'chiradi. True: o'chirildi; False: topilmadi."""
    async with async_session() as session:
        async with session.begin():
            channel = await session.scalar(
                select(Channel).where(Channel.channel_id == channel_id)
            )
            if not channel:
                return False
            await session.delete(channel)
    logger.info("Kanal o'chirildi: id=%s", channel_id)
    return True
