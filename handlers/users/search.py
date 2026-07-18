"""
Kino qidiruv handleri (faqat private chat).
Majburiy obuna → kino yuborish tartibida ishlaydi.
"""
from __future__ import annotations

from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config.config import GROUP_ID, ADMINS
from database.requests import get_movie, get_all_channels, is_referral_exempt, record_missed_search
from utils.helpers import get_bot_username, build_movie_keyboard
from utils.logger import get_logger

logger = get_logger(__name__)
router = Router()


async def check_subscriptions(
    bot, user_id: int, channels: list
) -> list:
    """Obuna bo'lmagan kanallar ro'yxatini qaytaradi."""
    unsubscribed = []
    for channel in channels:
        try:
            member = await bot.get_chat_member(
                chat_id=channel.channel_id, user_id=user_id
            )
            if member.status in ("left", "kicked", "banned"):
                unsubscribed.append(channel)
        except Exception as exc:
            logger.warning(
                "get_chat_member xatosi: channel_id=%s, xato=%s",
                channel.channel_id, exc,
            )
            unsubscribed.append(channel)
    return unsubscribed


@router.message(F.chat.type == "private", F.text)
async def search_movie(message: types.Message) -> None:
    user = message.from_user
    if user is None:
        return

    kino_kodi = (message.text or "").strip()

    if not kino_kodi.isdigit():
        await message.answer(
            "⚠️ Iltimos, faqat kino <b>raqamli kodini</b> yuboring.\n"
            "<i>Masalan: 71</i>",
            parse_mode="HTML",
        )
        return

    # Adminlar va yetarli do'st taklif qilganlarga majburiy obuna tekshiruvi kerak emas
    skip_subscription = user.id in ADMINS or await is_referral_exempt(user.id)
    await send_movie_checked(message, kino_kodi, skip_subscription=skip_subscription)


async def send_movie_checked(
    message: types.Message,
    kino_kodi: str,
    *,
    user_id: int | None = None,
    skip_subscription: bool = False,
    intro_text: str | None = None,
) -> None:
    """
    Majburiy obunani tekshirib (agar kerak bo'lsa), keyin kinoni yuboradi.
    Deep-link (/start <kod>), oddiy qidiruv va sevimlilar/katalog ro'yxatidan
    qayta yuborish shu funksiyadan foydalanadi.

    user_id — kimning obunasi tekshirilishi kerakligi. Berilmasa message.from_user.id
    ishlatiladi (oddiy xabar holatida to'g'ri); callback orqali chaqirilganda
    (message = call.message, ya'ni botning o'z xabari) buni aniq uzatish shart,
    aks holda bot o'zining obunasi tekshirilib qoladi.
    """
    user_id = user_id if user_id is not None else message.from_user.id

    if not skip_subscription:
        channels = await get_all_channels()
        if channels:
            unsubscribed = await check_subscriptions(message.bot, user_id, channels)
            if unsubscribed:
                builder = InlineKeyboardBuilder()
                for ch in unsubscribed:
                    builder.button(text=f"📢 {ch.title}", url=ch.link)
                builder.button(
                    text="✅ Obunani tekshirish",
                    callback_data=f"checksub_{kino_kodi}",
                )
                builder.adjust(1)

                await message.answer(
                    "📢 <b>Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:</b>",
                    reply_markup=builder.as_markup(),
                    parse_mode="HTML",
                )
                return

    await _send_movie(message, kino_kodi, user_id=user_id, intro_text=intro_text)


async def _send_movie(
    message: types.Message,
    kino_kodi: str,
    *,
    user_id: int | None = None,
    intro_text: str | None = None,
) -> None:
    """Foydalanuvchiga kino yuboradi."""
    user_id = user_id if user_id is not None else message.from_user.id
    message_id = await get_movie(kino_kodi)

    if not message_id:
        await record_missed_search(kino_kodi)
        await message.answer(
            f"😔 Kechirasiz, <b>{kino_kodi}</b> kodli kino topilmadi.\n"
            f"Balki kodni to'g'ri yozdingiz yana bir bor tekshiring.",
            parse_mode="HTML",
        )
        return

    try:
        if intro_text:
            await message.answer(intro_text)

        bot_username = await get_bot_username(message.bot)
        keyboard = build_movie_keyboard(bot_username, kino_kodi)

        await message.bot.copy_message(
            chat_id=message.chat.id,
            from_chat_id=GROUP_ID,
            message_id=message_id,
            reply_markup=keyboard,
            protect_content=True,
        )
        logger.info("Kino yuborildi: user_id=%s, kod=%s", user_id, kino_kodi)
    except Exception as exc:
        logger.error(
            "Kino yuborishda xato: kod=%s, xato=%s", kino_kodi, exc
        )
        await message.answer(
            "❌ Kechirasiz, kinoni yuklashda xatolik yuz berdi. "
            "Iltimos, keyinroq urinib ko'ring."
        )
