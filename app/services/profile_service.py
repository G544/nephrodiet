from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import Profile

PROFILE_ID = 1


async def get_profile(session: AsyncSession) -> Profile | None:
    return await session.get(Profile, PROFILE_ID)


async def upsert_profile(session: AsyncSession, data: dict) -> Profile:
    profile = await session.get(Profile, PROFILE_ID)
    if profile is None:
        profile = Profile(id=PROFILE_ID, **data)
    else:
        for key, value in data.items():
            setattr(profile, key, value)
        profile.updated_at = datetime.now(UTC)
    session.add(profile)
    await session.flush()
    return profile
