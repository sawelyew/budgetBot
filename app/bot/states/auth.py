from aiogram.fsm.state import State, StatesGroup


class RegistrationState(StatesGroup):
    full_name = State()
    department = State()
    custom_department = State()
    default_requisites = State()

    
class UserSettingsState(StatesGroup):
    change_requisites = State()