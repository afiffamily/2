from aiogram import Router, types, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config.config import GROUP_ID, ADMINS
from database.requests import get_movie, add_user
from admins.admin_panel import get_admin_keyboard

router = Router()

@router.message(CommandStart(), F.chat.type == "private")
async def cmd_start(message: types.Message, command: CommandObject):
    user_id = message.from_user.id
    full_name = message.from_user.full_name
    await add_user(telegram_id=user_id, full_name=full_name)
    if user_id in ADMINS:
        await message.answer(
            f"👨‍💻 Xush kelibsiz, Boshqaruvchi!\n\n"
            f"Siz bekorchi emassiz, kino ko'rib o'tirmaysiz! Botni boshqaring! 😎",
            reply_markup=get_admin_keyboard()
        )
        return 
    
    payload = command.args
    if payload and payload.isdigit():
        kino_kodi = payload
        message_id = await get_movie(kino_kodi)
        
        if message_id:
            try:
                bot_info = await message.bot.get_me()
                bot_username = bot_info.username
                share_url = f"https://t.me/share/url?url=https://t.me/{bot_username}?start={kino_kodi}&text=Tavsiya qilaman! 🎬"
                
                builder = InlineKeyboardBuilder()
                builder.button(text="🔥 Zo'r", callback_data=f"rate_like_{kino_kodi}")
                builder.button(text="👎 Yoqmadi", callback_data=f"rate_dislike_{kino_kodi}")
                builder.button(text="↗️ Do'stga yuborish", url=share_url)
                builder.adjust(2, 1)

                await message.answer("🎉 Sizga do'stingizdan maxsus kino yetib keldi:")
                await message.bot.copy_message(
                    chat_id=message.chat.id,
                    from_chat_id=GROUP_ID,
                    message_id=message_id,
                    reply_markup=builder.as_markup(),
                    protect_content=True
                )
                return 
            except Exception:
                pass 

    text = (
        f"Assalomu alaykum, <b>{full_name}</b>! 👋\n\n"
        f"🎬 Eng sara kinolarni topish botiga xush kelibsiz.\n"
        f"Kino qidirish uchun menga kerakli <b>kino kodini</b> yuboring.\n\n"
        f"<i>Masalan: 71</i>"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())