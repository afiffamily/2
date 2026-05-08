import re
from aiogram import Router, types, F
from config.config import GROUP_ID
from database.requests import add_movie 

router = Router()

@router.message(F.chat.id == GROUP_ID)
async def catch_movie_post(message: types.Message):
    text = message.text or message.caption
    
    if text:
        match = re.search(r"Kino kodi:\s*(\d+)", text, re.IGNORECASE)
        if match:
            kino_kodi = match.group(1)
            
            await add_movie(kino_kodi, message.message_id)
            
            await message.reply(f"✅ {kino_kodi}-kodli tayyor! Baza yangilandi.")