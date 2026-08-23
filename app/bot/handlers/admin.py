from aiogram import Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.filters import Command, CommandObject

from app.bot.filters.admin import IsAdmin
from app.db.repositories.user import UserRepository

router = Router()


@router.message(Command("setrole"), IsAdmin())
async def change_user_role(message: Message, command: CommandObject, session: AsyncSession):
    if not command.args:
        await message.answer("Использование: `/setrole <telegram_id> <ADMIN|FINANCIER|APPLICANT>`")
        return

    args = command.args.split()
    if len(args) < 2:
        await message.answer("Укажите telegram_id и роль!")
        return

    target_tg_id, new_role = int(args[0]), args[1].upper()

    user_repo = UserRepository(session)
    updated_user = await user_repo.update_role(telegram_id=target_tg_id, new_role=new_role)

    if updated_user:
        await message.answer(f"👤 Роль пользователя {updated_user.full_name} изменена на `{new_role}`")
        await message.bot.send_message(
            chat_id=target_tg_id,
            text=f"⚙️ Ваша роль в системе была изменена на: **{new_role}**"
        )
    else:
        await message.answer("Пользователь с таким Telegram ID не найден.")