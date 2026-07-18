"""
Inline tugmalar callback handlerlari.
"""
from __future__ import annotations

from aiogram import Router, types, F

from config.config import ADMINS, GROUP_ID
from database.requests import (
    rate_movie,
    get_movie,
    get_all_channels,
    is_referral_exempt,
    record_missed_search,
    toggle_favorite,
)
from handlers.users.search import check_subscriptions, send_movie_checked
from utils.helpers import get_bot_username, build_movie_keyboard
from utils.logger import get_logger

logger = get_logger(__name__)
router = Router()


# ── Like / Dislike ─────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("rate_"))
async def handle_rating(call: types.CallbackQuery) -> None:
    """
    rate_like_<kino_kodi> yoki rate_dislike_<kino_kodi> formatida.
    maxsplit=2 bilan to'g'ri parse qilamiz.
    """
    parts = call.data.split("_", maxsplit=2)
    if len(parts) != 3:
        await call.answer("⚠️ Noto'g'ri format!", show_alert=True)
        return

    _, action, kino_kodi = parts
    if action not in ("like", "dislike"):
        await call.answer("⚠️ Noto'g'ri amal!", show_alert=True)
        return

    result = await rate_movie(kino_kodi, action, call.from_user.id)
    if result == "ok":
        text = "🔥 Ovoz berganingiz uchun rahmat!" if action == "like" else "😔 Fikringiz qabul qilindi."
        await call.answer(text=text, show_alert=False)
        logger.debug("Reyting: user_id=%s, kod=%s, action=%s", call.from_user.id, kino_kodi, action)
    elif result == "already_voted":
        await call.answer("⚠️ Siz bu kinoga allaqachon ovoz bergansiz.", show_alert=True)
    else:
        await call.answer("⚠️ Xatolik! Kino topilmadi.", show_alert=True)


# ── Sevimlilar ──────────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("fav_"))
async def handle_favorite(call: types.CallbackQuery) -> None:
    """fav_<kino_kodi> — kino kartochkasidagi "⭐ Saqlash" tugmasi."""
    kino_kodi = call.data.removeprefix("fav_")
    added = await toggle_favorite(call.from_user.id, kino_kodi)
    if added:
        await call.answer("⭐ Sevimlilarga qo'shildi!", show_alert=False)
    else:
        await call.answer("🗑 Sevimlilardan olib tashlandi.", show_alert=False)


@router.callback_query(F.data.startswith("sendcode_"))
async def resend_by_code(call: types.CallbackQuery) -> None:
    """sendcode_<kino_kodi> — sevimlilar yoki katalog ro'yxatidan kinoni qayta yuborish."""
    kino_kodi = call.data.removeprefix("sendcode_")
    user_id = call.from_user.id
    skip_subscription = user_id in ADMINS or await is_referral_exempt(user_id)
    await call.answer()
    await send_movie_checked(
        call.message, kino_kodi, user_id=user_id, skip_subscription=skip_subscription
    )


# ── Obunani tekshirish ─────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("checksub_"))
async def verify_subscription(call: types.CallbackQuery) -> None:
    """checksub_<kino_kodi> formatida."""
    kino_kodi = call.data.removeprefix("checksub_")
    user_id = call.from_user.id

    channels = await get_all_channels()
    unsubscribed = await check_subscriptions(call.bot, user_id, channels)

    if unsubscribed:
        await call.answer(
            "❌ Siz hali barcha kanallarga obuna bo'lmadingiz!",
            show_alert=True,
        )
        return

    # Obuna tasdiqlandi → kinoni yuboramiz
    await call.message.delete()
    await call.message.answer("🎉 Obuna uchun rahmat! Mana siz qidirgan kino:")

    message_id = await get_movie(kino_kodi)
    if not message_id:
        await record_missed_search(kino_kodi)
        await call.message.answer("😔 Kechirasiz, bunday kodli kino topilmadi.")
        return

    try:
        bot_username = await get_bot_username(call.bot)
        keyboard = build_movie_keyboard(bot_username, kino_kodi)

        await call.bot.copy_message(
            chat_id=call.message.chat.id,
            from_chat_id=GROUP_ID,
            message_id=message_id,
            reply_markup=keyboard,
            protect_content=True,
        )
        logger.info(
            "Obunadan so'ng kino yuborildi: user_id=%s, kod=%s", user_id, kino_kodi
        )
    except Exception as exc:
        logger.error("checksub kinoni yuborishda xato: kod=%s, xato=%s", kino_kodi, exc)
        await call.message.answer(
            "❌ Kechirasiz, kinoni yuklashda xatolik yuz berdi."
        )
