"""
Umumiy yordamchi funksiyalar (kesh, URL yaratish va h.k.)
"""
from __future__ import annotations

from urllib.parse import quote

from aiogram import Bot

# Bot username ni bir marta cache'laymiz (har so'rovda API chaqirmaymiz)
_bot_username_cache: str | None = None


async def get_bot_username(bot: Bot) -> str:
    """Bot username ni cached tarzda qaytaradi."""
    global _bot_username_cache
    if _bot_username_cache is None:
        me = await bot.get_me()
        _bot_username_cache = me.username
    return _bot_username_cache


def build_share_url(bot_username: str, kino_kodi: str) -> str:
    """Kino uchun ulashish (share) URL yaratadi."""
    deep_link = f"https://t.me/{bot_username}?start={kino_kodi}"
    text = "Zo'r kino! Ko'rmasang bo'lmaydi 🎬🔥"
    return f"https://t.me/share/url?url={quote(deep_link, safe='')}&text={quote(text)}"


def build_movie_keyboard(bot_username: str, kino_kodi: str):
    """Kino kartochkasi uchun inline klaviatura yaratadi."""
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    share_url = build_share_url(bot_username, kino_kodi)
    builder = InlineKeyboardBuilder()
    builder.button(text="🔥 Zo'r", callback_data=f"rate_like_{kino_kodi}")
    builder.button(text="👎 Yoqmadi", callback_data=f"rate_dislike_{kino_kodi}")
    builder.button(text="⭐ Saqlash", callback_data=f"fav_{kino_kodi}")
    builder.button(text="↗️ Do'stga yuborish", url=share_url)
    builder.adjust(2, 2)
    return builder.as_markup()
