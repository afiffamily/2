from __future__ import annotations

from aiogram import Router, F, types
from aiogram.filters import Command, CommandStart, CommandObject

from config.config import ADMINS, REFERRAL_THRESHOLD
from database.requests import add_user, get_referral_count, is_referral_exempt
from handlers.users.search import send_movie_checked
from utils.helpers import get_bot_username

router = Router()


@router.message(CommandStart(), F.chat.type == "private")
async def cmd_start(message: types.Message, command: CommandObject) -> None:
    user = message.from_user
    if user is None:
        return

    payload = (command.args or "").strip()

    # Referral deep-link: ?start=ref_<taklif_qilgan_user_id>
    referred_by: int | None = None
    if payload.startswith("ref_"):
        ref_part = payload.removeprefix("ref_")
        if ref_part.isdigit():
            referred_by = int(ref_part)

    await add_user(
        telegram_id=user.id,
        full_name=user.full_name,
        username=user.username,
        referred_by=referred_by,
    )

    if payload.isdigit():
        # Majburiy obuna deep-link orqali ham tekshiriladi — oddiy qidiruv bilan bir xil qoida.
        skip_subscription = user.id in ADMINS or await is_referral_exempt(user.id)
        await send_movie_checked(
            message,
            payload,
            skip_subscription=skip_subscription,
            intro_text="🎉 Sizga do'stingizdan maxsus kino yetib keldi:",
        )
        return

    if user.id in ADMINS:
        from admins.admin_panel import get_admin_keyboard
        await message.answer(
            f"👨‍💻 Xush kelibsiz, Boshqaruvchi!\n\n"
            f"Botni boshqaring! 😎",
            reply_markup=get_admin_keyboard(),
        )
        return

    await message.answer(
        f"Assalomu alaykum, <b>{user.full_name}</b>! 👋\n\n"
        f"🎬 Eng sara kinolarni topish botiga xush kelibsiz.\n"
        f"Kino qidirish uchun menga <b>kino kodini</b> yuboring.\n\n"
        f"<i>Masalan: 71</i>",
        parse_mode="HTML",
        reply_markup=types.ReplyKeyboardRemove(),
    )


@router.message(Command("referal"), F.chat.type == "private")
async def cmd_referral(message: types.Message) -> None:
    """Foydalanuvchining referral holatini va ulashish havolasini ko'rsatadi."""
    user = message.from_user
    if user is None:
        return

    count = await get_referral_count(user.id)
    bot_username = await get_bot_username(message.bot)
    ref_link = f"https://t.me/{bot_username}?start=ref_{user.id}"

    if count >= REFERRAL_THRESHOLD:
        status = "✅ Siz allaqachon majburiy obunadan ozod qilingansiz!"
    else:
        qolgan = REFERRAL_THRESHOLD - count
        status = (
            f"Yana <b>{qolgan}</b> ta do'stingiz botdan foydalansa, "
            f"majburiy obunadan butunlay ozod bo'lasiz!"
        )

    await message.answer(
        f"🎁 Siz <b>{count}/{REFERRAL_THRESHOLD}</b> do'st taklif qildingiz.\n"
        f"{status}\n\n"
        f"Ulashish havolangiz:\n{ref_link}",
        parse_mode="HTML",
    )