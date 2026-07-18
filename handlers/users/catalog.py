"""
Katalog — kod bilmasdan oxirgi qo'shilgan kinolarni ko'rish.
"sendcode_<kod>" callbacki handlers/users/callbacks.py da joylashgan.
"""
from __future__ import annotations

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.requests import get_recent_movies

router = Router()


@router.message(Command("yangi"), F.chat.type == "private")
async def show_recent_movies(message: types.Message) -> None:
    movies = await get_recent_movies(limit=10)
    if not movies:
        await message.answer("😔 Hozircha bazada kinolar yo'q.")
        return

    lines = ["🆕 <b>Oxirgi qo'shilgan kinolar:</b>\n"]
    builder = InlineKeyboardBuilder()
    for movie in movies:
        sana = movie.created_at.strftime("%d.%m.%Y")
        lines.append(f"🎬 <code>{movie.kino_kodi}</code> | 👍 {movie.likes} | {sana}")
        builder.button(text=f"📽 {movie.kino_kodi}", callback_data=f"sendcode_{movie.kino_kodi}")
    builder.adjust(2)

    await message.answer("\n".join(lines), reply_markup=builder.as_markup(), parse_mode="HTML")
