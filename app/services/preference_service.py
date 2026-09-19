from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.preference import Preference


async def list_preferences(session: AsyncSession, active_only: bool = False) -> list[Preference]:
    stmt = select(Preference).order_by(Preference.created_at)
    if active_only:
        stmt = stmt.where(Preference.active.is_(True))
    result = await session.execute(stmt)
    return list(result.scalars())


async def add_preference(session: AsyncSession, phrase: str) -> Preference:
    preference = Preference(phrase=phrase)
    session.add(preference)
    await session.flush()
    return preference


async def set_active(session: AsyncSession, preference_id: int, active: bool) -> Preference | None:
    preference = await session.get(Preference, preference_id)
    if preference is None:
        return None
    preference.active = active
    session.add(preference)
    await session.flush()
    return preference


async def delete_preference(session: AsyncSession, preference_id: int) -> bool:
    preference = await session.get(Preference, preference_id)
    if preference is None:
        return False
    await session.delete(preference)
    return True
