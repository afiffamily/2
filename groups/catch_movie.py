"""
Guruh channelidan kino xabarlarini ushlash.
Format: caption/text ichida "Kino kodi: <raqam>" bo'lishi kerak.
"""
from __future__ import annotations

import re

from aiogram import Router, types, F

from config.config import GROUP_ID
from database.requests import add_movie
from filters.is_group import IsTargetGroup
from utils.logger import get_logger

logger = get_logger(__name__)
router = Router()

# Kino kodi regex: "Kino kodi: 123" yoki "kino kodi:123"
_KINO_CODE_RE = re.compile(r"kino\s*kodi\s*:\s*(\d+)", re.IGNORECASE)

# Reklama qo'shimchasi (kerak bo'lmasa bo'sh qoldiring)
AD_SUFFIX = "\n\n🤖 Tekin AI yordamchi: <a href='https://t.me/uzchatgptaibot'>ChatGPT AI</a>"


@router.message(IsTargetGroup(), F.chat.type.in_({"group", "supergroup"}))
async def catch_movie_post(message: types.Message) -> None:
    """
    Guruhga yuborilgan kino xabarini ushlab, bazaga saqlaydi.
    Faqat video, document yoki photo bo'lsa ishlaydi.
    """
    raw_text: str = message.text or message.caption or ""
    match = _KINO_CODE_RE.search(raw_text)
    if not match:
        # Kino kodi yo'q — oddiy guruh xabari, e'tibor bermayiz
        return

    kino_kodi = match.group(1)
    html_text: str = message.html_text or raw_text
    new_caption = html_text + AD_SUFFIX

    # Media turini aniqlash
    try:
        sent_msg: types.Message | None = None

        if message.video:
            sent_msg = await message.answer_video(
                video=message.video.file_id,
                caption=new_caption,
                parse_mode="HTML",
            )
        elif message.document:
            sent_msg = await message.answer_document(
                document=message.document.file_id,
                caption=new_caption,
                parse_mode="HTML",
            )
        elif message.photo:
            sent_msg = await message.answer_photo(
                photo=message.photo[-1].file_id,
                caption=new_caption,
                parse_mode="HTML",
            )
        else:
            logger.debug("Guruh xabari media emas, o'tkazib yuborildi.")
            return

        if sent_msg is None:
            return

        is_new = await add_movie(kino_kodi, sent_msg.message_id)
        await message.delete()

        status = "Yangi kino" if is_new else "Kino yangilandi"
        await message.answer(
            f"✅ {status}: kod <code>{kino_kodi}</code>. Baza yangilandi.",
            parse_mode="HTML",
        )
        logger.info(
            "%s saqlandi: kod=%s, message_id=%s", status, kino_kodi, sent_msg.message_id
        )

    except Exception as exc:
        logger.error("Guruh kinoni saqlashda xato: kod=%s, xato=%s", kino_kodi, exc)
        await message.answer(
            "❌ Xatolik: Bot guruhda to'liq admin huquqlariga ega emasmi yoki format xato."
        )
