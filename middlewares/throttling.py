"""
Throttling (tezlik cheklash) middleware.
Foydalanuvchini spam qilishdan himoya qiladi.
"""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from config.config import THROTTLE_RATE, THROTTLE_LIMIT
from utils.logger import get_logger

logger = get_logger(__name__)


class ThrottlingMiddleware(BaseMiddleware):
    """
    Sliding window algoritmiga asoslangan throttling.
    - THROTTLE_RATE: vaqt oynasi (soniya)
    - THROTTLE_LIMIT: oynada ruxsat etilgan so'rovlar soni
    """

    def __init__(
        self,
        rate: float = THROTTLE_RATE,
        limit: int = THROTTLE_LIMIT,
    ) -> None:
        self.rate = rate
        self.limit = limit
        # {user_id: [timestamp1, timestamp2, ...]}
        self._history: dict[int, list[float]] = defaultdict(list)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        if user is None:
            return await handler(event, data)

        user_id = user.id
        now = time.monotonic()

        # Eski tarixni tozalash
        history = self._history[user_id]
        self._history[user_id] = [t for t in history if now - t < self.rate]

        if len(self._history[user_id]) >= self.limit:
            logger.warning("Throttled user_id=%s", user_id)
            warning = "⏳ Iltimos, biroz sekinroq! Juda ko'p so'rov yubordingiz."
            if isinstance(event, CallbackQuery):
                await event.answer(warning, show_alert=True)
            elif isinstance(event, Message):
                await event.answer(warning)
            return None  # Handlega o'tkazmaymiz

        self._history[user_id].append(now)
        return await handler(event, data)
