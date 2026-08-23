from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_requisites_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Изменить реквизиты",
                    callback_data="change_requisites"
                )
            ]
        ]
    )