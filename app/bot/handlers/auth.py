from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.states.auth import RegistrationState
from app.db.models.user import User
from app.db.repositories.user import UserRepository
from app.config import config as settings
from app.bot.keyboards.admin import get_user_approval_keyboard

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, user: User | None, state: FSMContext):
    if user:
        await message.answer(
            f"👋 Привет, {user.full_name}!\n"
            f"Используй меню для отправки запроса на возврат средств или работы с заявками."
        )
        return

    await state.set_state(RegistrationState.full_name)
    await message.answer(
        "👋 **Добро пожаловать в бота бюджета активностей!**\n\n"
        "Для начала работы необходимо пройти регистрацию.\n"
        "Введите ваше **ФИО** (например: Иванов Иван Иванович):"
    )


@router.message(RegistrationState.full_name)
async def process_full_name(message: Message, state: FSMContext):
    if message.text and message.text.startswith("/"):
        await message.answer("⚠️ Пожалуйста, введите ваше ФИО текстом, а не командой:")
        return

    await state.update_data(full_name=message.text.strip())
    await state.set_state(RegistrationState.default_requisites)
    await message.answer(
        text=(
            "Укажите ваши **реквизиты для выплаты по умолчанию**\n"
            "(например: `+375291234567 / Приорбанк` или `4276.... / Сбер`):"
        )
    )


@router.message(RegistrationState.default_requisites)
async def process_requisites(message: Message, state: FSMContext, session: AsyncSession):
    if message.text and message.text.startswith("/"):
        await message.answer("⚠️ Пожалуйста, введите реквизиты текстом, а не командой:")
        return

    data = await state.get_data()
    user_repo = UserRepository(session)

    user = await user_repo.create_user(
        telegram_id=message.from_user.id,
        full_name=data["full_name"],
        default_requisites=message.text.strip(),
    )

    await state.clear()
    await message.answer(
        "✅ **Заявка на регистрацию успешно отправлена!**\n"
        "Ожидайте подтверждения доступа от администратора."
    )


    await message.bot.send_message(
        chat_id=settings.admin_chat_id,
        text=(
            f"🆕 **Заявка на регистрацию в боте**\n\n"
            f"👤 **ФИО:** {user.full_name}\n"
            f"🆔 **Telegram ID:** `{user.telegram_id}`\n"
            f"🏷 **Username:** @{message.from_user.username or 'нет'}"
        ),
        reply_markup=get_user_approval_keyboard(user.telegram_id),
    )