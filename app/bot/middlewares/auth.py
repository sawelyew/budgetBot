from collections.abc import Awaitable, Callable
from typing import Any
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TgUser
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.types import Message, CallbackQuery
from app.db.models.user import User

from app.db.repositories.user import UserRepository


class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        event_user: TgUser | None = data.get("event_from_user")
        if not event_user:
            return await handler(event, data)

        session: AsyncSession = data["session"]
        user_repo = UserRepository(session)
        user = await user_repo.get_by_id(event_user.id)

        current_state = await data.get("state").get_state() if data.get("state") else None
        if not user and current_state and current_state.startswith("RegistrationState"):
            return await handler(event, data)

        if not user:
            data["user"] = None
            return await handler(event, data)

        if not user.is_approved:
            if hasattr(event, "message") and event.message:
                await event.message.answer(
                    "**Ваш аккаунт ожидает подтверждения администратором.**\n"
                    "После одобрения вам станет доступен полный функционал бота."
                )
            elif hasattr(event, "callback_query") and event.callback_query:
                await event.callback_query.answer(
                    "Ваш аккаунт ожидает подтверждения администратором.",
                    show_alert=True,
                )
            return

        data["user"] = user
        return await handler(event, data)


class ApprovedUserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: dict[str, Any]
    ) -> Any:
        user: User | None = data.get("user")

        if not user:
            return await handler(event, data)

        if not user.is_approved:
            text = "⏳ Ваша заявка на доступ находится на рассмотрении у администратора."
            if isinstance(event, Message):
                await event.answer(text)
            elif isinstance(event, CallbackQuery):
                await event.answer(text, show_alert=True)
            return

        return await handler(event, data)