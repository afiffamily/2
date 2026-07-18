"""
Admin filtri.
Har bir handlerda if-check yozish o'rniga shu filtrni ishlatamiz.
"""
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

from config.config import ADMINS


class IsAdmin(BaseFilter):
    """Foydalanuvchi ADMINS ro'yxatida bo'lsa True qaytaradi."""

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user = event.from_user
        return user is not None and user.id in ADMINS
