"""
Guruh filtri — faqat belgilangan GROUP_ID dan kelgan xabarlar.
"""
from aiogram.filters import BaseFilter
from aiogram.types import Message

from config.config import GROUP_ID


class IsTargetGroup(BaseFilter):
    """Xabar faqat kino guruhi chatidan kelgan bo'lsa True."""

    async def __call__(self, message: Message) -> bool:
        return message.chat.id == GROUP_ID
