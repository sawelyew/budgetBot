from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User, UserRole
from app.db.models.expense import ExpenseStatus
from app.db.repositories.expense import ExpenseRepository

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