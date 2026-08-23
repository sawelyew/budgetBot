from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

EVENTS = ["Тур Тропа", "Капустник", "ФПМушка", "День Рождения Факультета", "Ввести вручную"]
DEPARTMENTS = ["IT отдел", "Креаторка", "Декораторка", "", "Ввести вручную"]


def get_events_keyboard() -> ReplyKeyboardMarkup:
    buttons = [[KeyboardButton(text=event)] for event in EVENTS]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)


def get_departments_keyboard() -> ReplyKeyboardMarkup:
    buttons = [[KeyboardButton(text=dept)] for dept in DEPARTMENTS]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)


def get_requisites_keyboard(default_req: str | None = None) -> InlineKeyboardMarkup:
    buttons = []

    if default_req:
        buttons.append([
            InlineKeyboardButton(
                text=f"Использовать по умолчанию ({default_req[:15]}...)",
                callback_data="req_default"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="Ввести новые реквизиты",
            callback_data="req_custom"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)