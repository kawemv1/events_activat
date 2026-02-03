import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from config import API_KEY
from database.engine import init_db
from handlers import start, settings, feedback, admin
from services.scheduler import start_scheduler, stop_scheduler, parse_and_save_events

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Основная функция запуска бота"""
    # Проверка наличия токена
    if not API_KEY:
        logger.error("API_KEY не найден в переменных окружения!")
        return

    # Инициализация базы данных
    logger.info("Инициализация базы данных...")
    init_db()
    logger.info("База данных инициализирована")

    # Создание бота и диспетчера
    bot = Bot(
        token=API_KEY,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Регистрация роутеров
    dp.include_router(start.router)
    dp.include_router(settings.router)
    dp.include_router(feedback.router)
    dp.include_router(admin.router)

    logger.info("Бот запущен")

    # Удаляем webhook если он установлен (чтобы избежать конфликтов)
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Webhook очищен")

    # Запуск планировщика
    start_scheduler(bot, run_immediately=True)
    
    # Запускаем первый парсинг сразу после старта (не блокируя запуск бота)
    import asyncio
    asyncio.create_task(parse_and_save_events(bot))

    try:
        # Запуск бота
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types(), drop_pending_updates=True)
    except Exception as e:
        logger.error(f"Ошибка при работе бота: {e}")
    finally:
        # Остановка планировщика
        stop_scheduler()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
