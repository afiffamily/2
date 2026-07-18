"""
Sevimlilar (bookmarks) — foydalanuvchi ko'rgan kinosini keyinroq topish uchun saqlaydi.
"fav_<kod>" (saqlash/olib tashlash) va "sendcode_<kod>" (qayta yuborish)
callbacklari handlers/users/callbacks.py da joylashgan.
"""
from __future__ import annotations

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.requests import get_user_favorites

router = Router()


@router.message(Command("sevimli"), F.chat.type == "private")
async def show_favorites(message: types.Message) -> None:
    user = message.from_user
    if user is None:
        return

    favorites = await get_user_favorites(user.id)
    if not favorites:
        await message.answer(
            "⭐ Sevimlilar ro'yxati bo'sh.\n\n"
            "Kino kartochkasidagi <b>⭐ Saqlash</b> tugmasini bosib, "
            "kinolarni shu yerga qo'shishingiz mumkin.",
            parse_mode="HTML",
        )
        return

    builder = InlineKeyboardBuilder()
    for kino_kodi in favorites:
        builder.button(text=f"📽 {kino_kodi}", callback_data=f"sendcode_{kino_kodi}")
    builder.adjust(2)

    await message.answer(
        "⭐ <b>Sizning sevimli kinolaringiz:</b>",
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )
