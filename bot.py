import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import API_KEY
from database.engine import init_db
from handlers import start, feedback, settings, admin, events
from services.scheduler import start_scheduler, run_parsing_cycle

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _run_initial_parse(bot: Bot):
    """Background: run one parsing cycle at startup."""
    try:
        logger.info("Running initial parsing cycle (background)...")
        await run_parsing_cycle(bot)
        logger.info("Initial parsing complete. events.csv updated.")
    except Exception as e:
        logger.error(f"Initial parsing failed: {e}")


async def main():
    init_db()
    bot = Bot(token=API_KEY)
    dp = Dispatcher()
    dp.include_routers(start.router, feedback.router, settings.router, admin.router, events.router)

    # Initial parsing run at startup in background (exports to events.csv)
    asyncio.create_task(_run_initial_parse(bot))

    # Daily updates at 10:00 (Asia/Almaty)
    start_scheduler(bot)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())