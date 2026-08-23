from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from app.db.models.user import User, UserRole

class IsAdmin(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery, user: User | None) -> bool:
        if not user:
            return False
        return user.role == UserRole.ADMIN

class IsAdminOrFinancier(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery, user: User | None) -> bool:
        if not user:
            return False
        return user.role == UserRole.ADMIN or user.role == UserRole.FINANCIER