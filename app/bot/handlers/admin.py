from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.filters import Command, CommandObject

from app.bot.filters.admin import IsAdminOrFinancier
from app.db.models.user import User
from app.db.repositories.expense import ExpenseRepository
from app.db.repositories.user import UserRepository


router = Router()
router.callback_query.filter(IsAdminOrFinancier())


@router.callback_query(F.data.startswith("approve_exp:"))
async def approve_expense(callback: CallbackQuery, session: AsyncSession, user: User):
    expense_id = int(callback.data.split(":")[1])

    expense_repo = ExpenseRepository(session)
    expense = await expense_repo.update_status(
        expense_id=expense_id,
        status="APPROVED",
        processed_by_id=user.telegram_id
    )

    await callback.bot.send_message(
        chat_id=expense.user_id,
        text=f"✅ Ваша заявка №{expense_id} на сумму {expense.amount} руб. была **одобрена**!"
    )

    current_caption = callback.message.caption or callback.message.text or ""
    await callback.message.edit_caption(
        caption=f"{current_caption}\n\n🟢 **Одобрено:** {user.full_name}",
        reply_markup=None
    )
    await callback.answer("Заявка одобрена")


@router.callback_query(F.data.startswith("reject_exp:"))
async def reject_expense(callback: CallbackQuery, session: AsyncSession, user: User):
    expense_id = int(callback.data.split(":")[1])

    expense_repo = ExpenseRepository(session)
    expense = await expense_repo.update_status(
        expense_id=expense_id,
        status="REJECTED",
        processed_by_id=user.telegram_id
    )

    await callback.bot.send_message(
        chat_id=expense.user_id,
        text=f"❌ Ваша заявка №{expense_id} была **отклонена**."
    )

    current_caption = callback.message.caption or callback.message.text or ""
    await callback.message.edit_caption(
        caption=f"{current_caption}\n\n🔴 **Отклонено:** {user.full_name}",
        reply_markup=None
    )
    await callback.answer("Заявка отклонена")


@router.callback_query(F.data.startswith("approve_user:"))
async def approve_user_access(callback: CallbackQuery, session: AsyncSession, user: User):
    target_tg_id = int(callback.data.split(":")[1])

    user_repo = UserRepository(session)
    is_approved = await user_repo.approve_user(telegram_id=target_tg_id)

    if is_approved:
        await callback.bot.send_message(
            chat_id=target_tg_id,
            text="🎉 **Ваш доступ подтвержден!** Теперь вы можете пользоваться ботом."
        )

        current_caption = callback.message.caption or callback.message.text or ""
        await callback.message.edit_text(
            text=f"{current_caption}\n\n✅ **Доступ разрешил:** {user.full_name}"
        )
        await callback.answer("Пользователь одобрен")
    else:
        await callback.answer("Ошибка: пользователь не найден", show_alert=True)


@router.callback_query(F.data.startswith("reject_user:"))
async def reject_user_access(callback: CallbackQuery, session: AsyncSession, user: User):
    target_tg_id = int(callback.data.split(":")[1])

    user_repo = UserRepository(session)

    target_user = await user_repo.get_by_id(target_tg_id)
    if target_user:
        await session.delete(target_user)
        await session.commit()

        await callback.bot.send_message(
            chat_id=target_tg_id,
            text="❌ К сожалению, ваша заявка на доступ была отклонена."
        )

    current_caption = callback.message.caption or callback.message.text or ""
    await callback.message.edit_text(
        text=f"{current_caption}\n\n🔴 **Отклонил:** {user.full_name}"
    )
    await callback.answer("Заявка отклонена")


@router.message(Command("setrole"))
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