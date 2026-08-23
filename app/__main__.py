import asyncio
import logging
from aiogram.fsm.storage.memory import MemoryStorage
from app.config import config
from app.bot.middlewares.db import DbSessionMiddleware
from app.bot.middlewares.auth import AuthMiddleware
from app.bot.handlers.auth import router as auth_router
from app.bot.handlers.expense import router as expense_router
from app.bot.handlers.finance import router as finance_router
from app.bot.handlers.user import router as user_router
from app.bot.handlers.admin import router as admin_router
from app.services.s3 import s3_service
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from app.db.base import Base, engine
import app.db.models


logging.basicConfig(level=logging.INFO)


async def main():
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    dp = Dispatcher(storage=MemoryStorage())

    dp.update.middleware(DbSessionMiddleware())
    dp.update.middleware(AuthMiddleware())

    dp.include_router(auth_router)
    dp.include_router(expense_router)
    dp.include_router(finance_router)
    dp.include_router(user_router)
    dp.include_router(admin_router)

    await bot.set_my_commands([
        BotCommand(command="new_expense", description="Подать заявку на возврат средств"),
        BotCommand(command="requisites", description="Реквизиты по умолчанию"),
    ])

    try:
        await s3_service.init_bucket()
        logging.info("MinIO bucket initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize MinIO bucket: {e}")

    logging.info("Starting bot polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())