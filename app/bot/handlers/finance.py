from app.db.models.user import User, UserRole
from app.db.models.expense import ExpenseStatus
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.user import User
from app.db.repositories.expense import ExpenseRepository
from app.db.repositories.user import UserRepository
from app.bot.filters.admin import IsAdminOrFinancier

router = Router()


@router.callback_query(F.data.startswith("exp_"))
async def process_expense_action(callback: CallbackQuery, user: User, session: AsyncSession):
    if user.role not in [UserRole.FINANCIER, UserRole.ADMIN]:
        await callback.answer("У вас нет прав для обработки заявок.", show_alert=True)
        return

    action, expense_id_str = callback.data.split(":")
    expense_id = int(expense_id_str)
    expense_repo = ExpenseRepository(session)

    expense = await expense_repo.get_by_id(expense_id)
    if not expense:
        await callback.answer("Заявка не найдена.", show_alert=True)
        return

    status_map = {
        "exp_approve": (ExpenseStatus.APPROVED, "Заявка одобрена"),
        "exp_reject": (ExpenseStatus.REJECTED, "Заявка отклонена"),
        "exp_paid": (ExpenseStatus.PAID, "Деньги переведены"),
    }

    new_status, status_text = status_map[action]
    await expense_repo.update_status(expense_id, new_status, processed_by_id=user.telegram_id)

    await callback.message.edit_caption(
        caption=f"{callback.message.caption}\n\n**Статус обновлен:** {status_text} (Обработал: {user.full_name})"
    )
    await callback.answer(f"Статус изменен на: {new_status.value}")

    try:
        await callback.bot.send_message(
            chat_id=expense.user_id,
            text=f"**Статус вашей заявки №{expense.id} был изменен:**\n{status_text}",
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("approve_exp:"))
async def approve_expense(callback: CallbackQuery, session: AsyncSession, user: User):
    if user.role not in [UserRole.FINANCIER, UserRole.ADMIN]:
        await callback.answer("У вас нет прав для обработки заявок.", show_alert=True)
        return

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
    if user.role not in [UserRole.FINANCIER, UserRole.ADMIN]:
        await callback.answer("У вас нет прав для обработки заявок.", show_alert=True)
        return

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
    if user.role not in [UserRole.FINANCIER, UserRole.ADMIN]:
        await callback.answer("У вас нет прав для обработки пользователей.", show_alert=True)
        return

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
    if user.role not in [UserRole.FINANCIER, UserRole.ADMIN]:
        await callback.answer("У вас нет прав для обработки пользователей.", show_alert=True)
        return

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