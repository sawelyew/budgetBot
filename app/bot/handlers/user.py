from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.db.repositories.user import UserRepository
from app.bot.states.auth import UserSettingsState
from app.bot.keyboards.user import get_requisites_keyboard

router = Router()


@router.message(Command("requisites"))
async def cmd_show_requisites(message: Message, user: User):
    current_req = user.requisites[0].details if getattr(user, "requisites", None) else "Не указаны"

    await message.answer(
        text=f"📋 **Ваши реквизиты по умолчанию:**\n`{current_req}`",
        reply_markup=get_requisites_keyboard()
    )


@router.callback_query(F.data == "change_requisites")
async def start_change_requisites(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserSettingsState.change_requisites)

    await callback.message.answer(
        text=(
            "Введите **новые реквизиты** для выплат по умолчанию\n"
            "(например: `+375291234567 / Приорбанк` или `4276.... / Сбер`):"
        ),
        reply_markup=ReplyKeyboardRemove()
    )
    await callback.answer()


@router.message(UserSettingsState.change_requisites)
async def process_new_requisites(message: Message, state: FSMContext, session: AsyncSession, user: User):
    new_req = message.text.strip()

    user_repo = UserRepository(session)
    await user_repo.update_default_requisites(telegram_id=user.telegram_id, new_details=new_req)

    await state.clear()
    await message.answer(text=f"✅ Реквизиты по умолчанию успешно обновлены на:\n`{new_req}`")