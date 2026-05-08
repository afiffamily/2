import asyncio
import logging
from aiogram import Bot, Dispatcher

from config.config import BOT_TOKEN
from database.models import async_main
from handlers.users.start import router as start_router
from admins.admin_panel import router as admin_router 
from groups.catch_movie import router as catch_router
from handlers.users.callbacks import router as callbacks_router
from handlers.users.search import router as search_router

async def main():
    print("⏳ Bazaga ulanish kutilmoqda...")
    await async_main()
    print("✅ Ma'lumotlar bazasi tayyor!")

    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    dp.include_router(start_router)
    dp.include_router(admin_router)    
    dp.include_router(catch_router)
    dp.include_router(callbacks_router)
    dp.include_router(search_router)   
    
    print("🤖 Bot muvaffaqiyatli ishga tushdi...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())