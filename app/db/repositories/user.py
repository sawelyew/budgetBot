from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.user import Requisites, User, UserRole


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, telegram_id: int) -> User | None:
        stmt = (
            select(User)
            .options(selectinload(User.requisites))
            .where(User.telegram_id == telegram_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user(
        self,
        telegram_id: int,
        full_name: str,
        default_requisites: str,
        role: UserRole = UserRole.APPLICANT,
    ) -> User:
        user = User(
            telegram_id=telegram_id,
            full_name=full_name,
            role=role,
            is_approved=False,
        )
        self.session.add(user)

        requisite = Requisites(
            user_id=telegram_id,
            details=default_requisites,
            is_default=True,
        )
        self.session.add(requisite)

        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def approve_user(self, telegram_id: int) -> bool:
        stmt = (
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(is_approved=True)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def update_role(self, telegram_id: int, new_role: UserRole) -> User | None:
        stmt = (
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(role=new_role)
            .returning(User)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def update_default_requisites(self, telegram_id: int, new_details: str) -> Requisites:
        stmt = select(Requisites).where(
            Requisites.user_id == telegram_id, Requisites.is_default == True
        )
        result = await self.session.execute(stmt)
        requisite = result.scalar_one_or_none()

        if requisite:
            requisite.details = new_details
        else:
            requisite = Requisites(
                user_id=telegram_id, details=new_details, is_default=True
            )
            self.session.add(requisite)

        await self.session.commit()
        await self.session.refresh(requisite)
        return requisite

    async def get_financiers_and_admins(self) -> list[User]:
        stmt = select(User).where(
            User.role.in_([UserRole.FINANCIER, UserRole.ADMIN]),
            User.is_approved == True,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_users_by_role(self, role: UserRole) -> list[User]:
        stmt = select(User).where(
            User.role == role,
            User.is_approved.is_(True)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())