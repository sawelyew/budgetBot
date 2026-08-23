from decimal import Decimal
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.expense import ExpenseRequest, ExpenseStatus


class ExpenseRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_request(
        self,
        user_id: int,
        event_name: str,
        department: str,
        amount: Decimal,
        comment: str,
        receipt_s3_key: str,
        requisites_used: str,
    ) -> ExpenseRequest:
        expense = ExpenseRequest(
            user_id=user_id,
            event_name=event_name,
            department=department,
            amount=amount,
            comment=comment,
            receipt_s3_key=receipt_s3_key,
            requisites_used=requisites_used,
            status=ExpenseStatus.PENDING,
        )
        self.session.add(expense)
        await self.session.commit()
        await self.session.refresh(expense)
        return expense

    async def get_by_id(self, expense_id: int) -> ExpenseRequest | None:
        stmt = (
            select(ExpenseRequest)
            .options(selectinload(ExpenseRequest.user))
            .where(ExpenseRequest.id == expense_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_status(
        self,
        expense_id: int,
        status: ExpenseStatus,
        processed_by_id: int,
    ) -> ExpenseRequest | None:
        stmt = (
            update(ExpenseRequest)
            .where(ExpenseRequest.id == expense_id)
            .values(status=status, processed_by_id=processed_by_id)
        )
        await self.session.execute(stmt)
        await self.session.commit()
        return await self.get_by_id(expense_id)

    async def get_user_expenses(self, user_id: int) -> list[ExpenseRequest]:
        stmt = (
            select(ExpenseRequest)
            .where(ExpenseRequest.user_id == user_id)
            .order_by(ExpenseRequest.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())