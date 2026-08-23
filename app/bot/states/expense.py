from aiogram.fsm.state import State, StatesGroup


class ExpenseState(StatesGroup):
    event_name = State()
    custom_event_name = State()
    department = State()
    custom_department = State()
    amount = State()
    comment = State()
    receipt = State()
    requisites = State()