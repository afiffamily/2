import re
from aiogram import Router, types, F
from config.config import GROUP_ID
from database.requests import add_movie

router = Router()

@router.message(F.chat.id == GROUP_ID)
async def catch_movie_post(message: types.Message):
    plain_text = message.text or message.caption
    html_text = message.html_text 
    
    if plain_text:
        match = re.search(r"Kino kodi:\s*(\d+)", plain_text, re.IGNORECASE)
        if match:
            kino_kodi = match.group(1)
            
            ad_text = "\n\n🤖 Tekin AI yordamchi: <a href='https://t.me/uzchatgptaibot'>ChatGPT AI</a>"
            new_caption = (html_text or "") + ad_text
            
            try:
                if message.video:
                    sent_msg = await message.answer_video(video=message.video.file_id, caption=new_caption, parse_mode="HTML")
                elif message.document:
                    sent_msg = await message.answer_document(document=message.document.file_id, caption=new_caption, parse_mode="HTML")
                elif message.photo:
                    sent_msg = await message.answer_photo(photo=message.photo[-1].file_id, caption=new_caption, parse_mode="HTML")
                else:
                    return 

                await add_movie(kino_kodi, sent_msg.message_id)
                await message.delete()
                await message.answer(f"✅ {kino_kodi}-kodli tayyor! Baza yangilandi.")
                
            except Exception:
                await message.answer("❌ Xatolik: Bot guruhda to'liq admin emas yoki format xato.")
