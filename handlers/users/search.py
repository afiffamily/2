from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config.config import GROUP_ID
from database.requests import get_movie, get_all_channels 

router = Router()

@router.message(F.chat.type == "private")
async def search_movie(message: types.Message):
    kino_kodi = message.text.strip()
    
    if not kino_kodi.isdigit():
        await message.answer("⚠️ Iltimos, faqat kino kodini yuboring (Masalan: 1)")
        return
        
    # ==========================================
    # 1-BOSQICH: MAJBURIY OBUNANI TEKSHIRISH
    # ==========================================
    channels = await get_all_channels()
    unsubscribed_channels = []
    
    if channels:
        for channel in channels:
            try:
                member = await message.bot.get_chat_member(chat_id=channel.channel_id, user_id=message.from_user.id)
                if member.status in ["left", "kicked", "banned"]:
                    unsubscribed_channels.append(channel)
            except Exception:
                unsubscribed_channels.append(channel)
                
    if unsubscribed_channels:
        builder = InlineKeyboardBuilder()
        for ch in unsubscribed_channels:
            builder.button(text=f"➕ Obuna bo'lish", url=ch.link)
        builder.button(text="✅ Obunani tekshirish", callback_data=f"checksub_{kino_kodi}")
        builder.adjust(1) 
        
        await message.answer(
            "📢 <b>Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:</b>",
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
        return 

    # ==========================================
    # 2-BOSQICH: KINONI YUBORISH (Hamma shart bajarilsa)
    # ==========================================
    message_id = await get_movie(kino_kodi)
    
    if message_id:
        try:
            bot_info = await message.bot.get_me()
            bot_username = bot_info.username
            share_url = f"https://t.me/share/url?url=https://t.me/{bot_username}?start={kino_kodi}&text=Shu kinoni ko'rmasang bo'lmaydi! 🎬 Dahshat kino ekan 🔥"
            
            builder = InlineKeyboardBuilder()
            builder.button(text="🔥 Zo'r", callback_data=f"rate_like_{kino_kodi}")
            builder.button(text="👎 Yoqmadi", callback_data=f"rate_dislike_{kino_kodi}")
            builder.button(text="↗️ Do'stga yuborish", url=share_url)
            builder.adjust(2, 1)

            await message.bot.copy_message(
                chat_id=message.chat.id,
                from_chat_id=GROUP_ID,
                message_id=message_id,
                reply_markup=builder.as_markup(),
                protect_content=True
            )
        except Exception:
            await message.answer("❌ Kechirasiz, kinoni yuklashda xatolik yuz berdi.")
    else:
        await message.answer("😔 Kechirasiz, bunday kodli kino topilmadi.")