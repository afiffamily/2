from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config.config import GROUP_ID
from database.requests import rate_movie, get_movie, get_all_channels

router = Router()

# 1. Kino reytingini (Like/Dislike) ushlab oluvchi handler (oldingisi)
@router.callback_query(F.data.startswith("rate_"))
async def handle_rating(call: types.CallbackQuery):
    action = call.data.split("_")[1] 
    kino_kodi = call.data.split("_")[2] 
    
    success = await rate_movie(kino_kodi, action)
    if success:
        if action == "like":
            await call.answer(text="🔥 Ovoz berganingiz uchun rahmat!", show_alert=False)
        elif action == "dislike":
            await call.answer(text="😔 Fikringiz qabul qilindi.", show_alert=False)
    else:
        await call.answer(text="⚠️ Xatolik! Kino topilmadi.", show_alert=True)

# 2. YANGI: OBUNANI TEKSHIRISH TUGMASI UCHUN
@router.callback_query(F.data.startswith("checksub_"))
async def verify_subscription(call: types.CallbackQuery):
    kino_kodi = call.data.split("_")[1]
    user_id = call.from_user.id
    
    channels = await get_all_channels()
    is_subscribed = True
    
    for channel in channels:
        try:
            member = await call.bot.get_chat_member(chat_id=channel.channel_id, user_id=user_id)
            if member.status in ["left", "kicked", "banned"]:
                is_subscribed = False
                break
        except Exception:
            is_subscribed = False
            break
            
    if not is_subscribed:
        await call.answer("❌ Siz barcha kanallarga obuna bo'lmadingiz! Iltimos obuna bo'ling.", show_alert=True)
        return
    await call.message.delete()
    await call.message.answer("🎉 Obuna uchun rahmat! Marhamat, siz qidirgan kino:")
    
    message_id = await get_movie(kino_kodi)
    if message_id:
        try:
            bot_info = await call.bot.get_me()
            bot_username = bot_info.username
            share_url = f"https://t.me/share/url?url=https://t.me/{bot_username}?start={kino_kodi}&text=Shu kinoni tavsiya qilaman! 🎬🔥"
            
            builder = InlineKeyboardBuilder()
            builder.button(text="🔥 Zo'r", callback_data=f"rate_like_{kino_kodi}")
            builder.button(text="👎 Yoqmadi", callback_data=f"rate_dislike_{kino_kodi}")
            builder.button(text="↗️ Do'stga yuborish", url=share_url)
            builder.adjust(2, 1)

            await call.bot.copy_message(
                chat_id=call.message.chat.id,
                from_chat_id=GROUP_ID,
                message_id=message_id,
                reply_markup=builder.as_markup(),
                protect_content=True
            )
        except Exception:
            await call.message.answer("❌ Kechirasiz, yuklashda xatolik yuz berdi.")
    else:
        await call.message.answer("😔 Kechirasiz, bunday kodli kino topilmadi.")