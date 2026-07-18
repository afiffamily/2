"""
Kino Bot — asosiy ishga tushirish nuqtasi.
"""
import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from config.config import BOT_TOKEN
from database.models import async_main
from handlers.users.start import router as start_router
from handlers.users.callbacks import router as callbacks_router
from handlers.users.favorites import router as favorites_router
from handlers.users.catalog import router as catalog_router
from handlers.users.search import router as search_router
from admins.admin_panel import router as admin_router
from groups.catch_movie import router as catch_router
from middlewares.throttling import ThrottlingMiddleware
from utils.logger import setup_logging, get_logger

logger = get_logger(__name__)


async def main() -> None:
    # ── Logging ───────────────────────────────────────────────────────────────
    setup_logging()

    # ── Ma'lumotlar bazasi ────────────────────────────────────────────────────
    logger.info("Ma'lumotlar bazasiga ulanilmoqda...")
    await async_main()

    # ── Bot va Dispatcher ─────────────────────────────────────────────────────
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # ── Middleware ────────────────────────────────────────────────────────────
    throttling = ThrottlingMiddleware()
    dp.message.middleware(throttling)
    dp.callback_query.middleware(throttling)

    # ── Routerlar (tartib muhim!) ─────────────────────────────────────────────
    # Admin routeri birinchi — adminga tegishli xabarlar search_routerga o'tmasin
    dp.include_router(admin_router)
    dp.include_router(start_router)
    dp.include_router(catch_router)
    dp.include_router(callbacks_router)
    dp.include_router(favorites_router)
    dp.include_router(catalog_router)
    dp.include_router(search_router)    # Eng oxirida (catch-all)

    # ── Ishga tushirish ───────────────────────────────────────────────────────
    me = await bot.get_me()
    logger.info("Bot ishga tushdi: @%s (id=%s)", me.username, me.id)

    await bot.set_my_commands([
        BotCommand(command="start", description="Botni ishga tushirish"),
        BotCommand(command="yangi", description="🆕 Oxirgi qo'shilgan kinolar"),
        BotCommand(command="sevimli", description="⭐ Sevimli kinolarim"),
        BotCommand(command="referal", description="🎁 Do'st taklif qilish"),
    ])

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except asyncio.CancelledError:
        logger.info("Polling to'xtatildi.")
    finally:
        await bot.session.close()
        logger.info("Bot sessiyasi yopildi.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot foydalanuvchi tomonidan to'xtatildi (Ctrl+C).")
        sys.exit(0)
