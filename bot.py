import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import API_KEY
from database.engine import init_db
from handlers import start, feedback, settings, admin, events
from services.scheduler import start_scheduler

logging.basicConfig(level=logging.INFO)

async def main():
    init_db()
    
    bot = Bot(token=API_KEY)
    dp = Dispatcher()
    
    dp.include_routers(start.router, feedback.router, settings.router, admin.router, events.router)
    
    # Ежедневное обновление выставок в 10:00 (Asia/Almaty)
    start_scheduler(bot)
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())