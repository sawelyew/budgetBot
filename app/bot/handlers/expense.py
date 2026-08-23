from io import BytesIO
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.states.expense import ExpenseState
from app.bot.keyboards.expense import (
    get_events_keyboard,
    get_departments_keyboard,
    get_requisites_keyboard,
)
from app.db.repositories.expense import ExpenseRepository
from app.services.s3 import s3_service

from app.bot.keyboards.admin import get_expense_approval_keyboard
from app.db.models.user import User, UserRole
from app.db.repositories.user import UserRepository
from aiogram.types import BufferedInputFile
from app.bot.keyboards.expense import EVENTS, DEPARTMENTS
from app.config import config as settings_config

router = Router()


@router.message(Command("new_expense"))
async def start_expense(message: Message, state: FSMContext):
    await state.set_state(ExpenseState.event_name)
    await message.answer(
        "Выберите мероприятие из списка или введите название вручную:",
        reply_markup=get_events_keyboard(),
    )


@router.message(ExpenseState.event_name, F.text == "Ввести вручную")
async def process_event_custom_prompt(message: Message, state: FSMContext):
    await state.set_state(ExpenseState.custom_event_name)
    await message.answer(
        text="Введите название мероприятия текстом:",
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(ExpenseState.event_name, F.text.in_(EVENTS))
async def process_event_from_list(message: Message, state: FSMContext):
    await state.update_data(event_name=message.text.strip())
    await state.set_state(ExpenseState.department)
    await message.answer(
        text="Выберите ваш отдел:",
        reply_markup=get_departments_keyboard()
    )


@router.message(ExpenseState.custom_event_name)
async def process_custom_event_input(message: Message, state: FSMContext):
    if message.text.startswith("/"):
        await message.answer("Пожалуйста, введите название мероприятия текстом, а не командой:")
        return

    await state.update_data(event_name=message.text.strip())
    await state.set_state(ExpenseState.department)
    await message.answer(
        text="Выберите ваш отдел:",
        reply_markup=get_departments_keyboard()
    )


@router.message(ExpenseState.event_name)
async def process_event_invalid(message: Message):
    await message.answer(
        text="⚠️ Пожалуйста, выберите мероприятие из списка с помощью кнопок или нажмите **«Ввести вручную»**:",
        reply_markup=get_events_keyboard()
    )


@router.message(ExpenseState.department, F.text == "Ввести вручную")
async def process_department_custom_prompt(message: Message, state: FSMContext):
    await state.set_state(ExpenseState.custom_department)
    await message.answer(
        text="Введите название отдела текстом:",
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(ExpenseState.department, F.text.in_(DEPARTMENTS))
async def process_department_from_list(message: Message, state: FSMContext):
    await state.update_data(department=message.text.strip())
    await state.set_state(ExpenseState.amount)
    await message.answer(text="Введите сумму расхода (например: `150.50`):")


@router.message(ExpenseState.custom_department)
async def process_custom_department_input(message: Message, state: FSMContext):
    if message.text.startswith("/"):
        await message.answer("Пожалуйста, введите название отдела текстом, а не командой:")
        return

    await state.update_data(department=message.text.strip())
    await state.set_state(ExpenseState.amount)
    await message.answer(text="Введите сумму расхода (например: `150.50`):")


@router.message(ExpenseState.department)
async def process_department_invalid(message: Message):
    await message.answer(
        text="⚠️ Пожалуйста, выберите отдел из списка с помощью кнопок или нажмите **«Ввести вручную»**:",
        reply_markup=get_departments_keyboard()
    )


@router.message(ExpenseState.amount)
async def process_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", "."))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Введите корректное число больше нуля.")
        return

    await state.update_data(amount=amount)
    await state.set_state(ExpenseState.comment)
    await message.answer("Опишите подробный комментарий (на что именно ушли деньги):")


@router.message(ExpenseState.comment)
async def process_comment(message: Message, state: FSMContext):
    await state.update_data(comment=message.text.strip())
    await state.set_state(ExpenseState.receipt)
    await message.answer("Отправьте фото чека/накладной:")


@router.message(ExpenseState.receipt, F.photo | F.document)
async def process_receipt(message: Message, state: FSMContext, user: User, bot):
    if message.photo:
        file_id = message.photo[-1].file_id
        file_unique_id = message.photo[-1].file_unique_id
    elif message.document:
        if not message.document.mime_type or not message.document.mime_type.startswith("image/"):
            await message.answer("Пожалуйста, отправьте файл в формате изображения (JPG, PNG)!")
            return
        file_id = message.document.file_id
        file_unique_id = message.document.file_unique_id

    file_info = await bot.get_file(file_id)
    downloaded_file = await bot.download_file(file_info.file_path)

    # Загрузка в MinIO S3
    s3_key = f"receipts/{user.telegram_id}_{file_unique_id}.jpg"
    await s3_service.upload_file(BytesIO(downloaded_file.read()), s3_key)

    await state.update_data(receipt_s3_key=s3_key)
    await state.set_state(ExpenseState.requisites)

    # Берем реквизиты по умолчанию из первой записи
    default_req = user.requisites[0].details if user.requisites else "Не указаны"
    await message.answer(
        f"Укажите реквизиты для перевода:\nТекущие: `{default_req}`",
        reply_markup=get_requisites_keyboard(default_req),
    )


@router.callback_query(ExpenseState.requisites, F.data == "req_default")
async def process_req_default(
    callback: CallbackQuery, state: FSMContext, user: User, session: AsyncSession
):
    default_req = user.requisites[0].details if user.requisites else "Не указаны"
    await finalize_expense(callback.message, state, user, default_req, session)
    await callback.answer()


@router.callback_query(ExpenseState.requisites, F.data == "req_custom")
async def process_req_custom(callback: CallbackQuery):
    await callback.message.answer("Введите новые реквизиты текстом:")
    await callback.answer()


@router.message(ExpenseState.requisites)
async def process_req_custom_text(
    message: Message, state: FSMContext, user: User, session: AsyncSession
):
    await finalize_expense(message, state, user, message.text.strip(), session)


async def finalize_expense(
    message: Message,
    state: FSMContext,
    user: User,
    requisites: str,
    session: AsyncSession,
):
    data = await state.get_data()
    expense_repo = ExpenseRepository(session)

    expense = await expense_repo.create_request(
        user_id=user.telegram_id,
        event_name=data["event_name"],
        department=data["department"],
        amount=data["amount"],
        comment=data["comment"],
        receipt_s3_key=data["receipt_s3_key"],
        requisites_used=requisites,
    )

    await state.clear()
    await message.answer(
        f"🎉 **Заявка №{expense.id} успешно сформирована и отправлена финансистам!**"
    )

    receipt_bytes = await s3_service.get_file_bytes(data["receipt_s3_key"])
    photo_file = BufferedInputFile(receipt_bytes, filename="receipt.jpg")

    caption_text = (
        f"📥 **Новая заявка на возврат средств №{expense.id}**\n\n"
        f"👤 **Заявитель:** {user.full_name}\n"
        f"🏢 **Отдел:** {expense.department}\n"
        f"🎉 **Мероприятие:** {expense.event_name}\n"
        f"💰 **Сумма:** `{expense.amount} руб.`\n"
        f"💬 **Комментарий:** {expense.comment}\n"
        f"💳 **Реквизиты:** `{expense.requisites_used}`"
    )

    await message.bot.send_photo(
        chat_id=settings_config.admin_chat_id,
        photo=photo_file,
        caption=caption_text,
        reply_markup=get_expense_approval_keyboard(expense.id),
    )