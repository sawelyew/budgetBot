from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_expense_approval_keyboard(expense_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Одобрить",
                    callback_data=f"approve_exp:{expense_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"reject_exp:{expense_id}"
                ),
            ]
        ]
    )

def get_user_approval_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Подтвердить доступ",
                callback_data=f"approve_user:{user_id}"
            ),

            InlineKeyboardButton(
                text="❌ Отклонить",
                callback_data=f"reject_user:{user_id}"
            )
        ]
    ])