from datetime import UTC, datetime

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Profile(SQLModel, table=True):
    """Singleton row (id is always 1) holding the user's medical/physical parameters."""

    id: int = Field(default=1, primary_key=True)
    age: int
    weight_kg: float
    height_cm: float
    sex: str  # "male" | "female"
    activity_level: str  # "sedentary" | "light" | "moderate" | "active"
    egfr: float | None = None
    salt_limit_g: float
    protein_limit_g: float
    goal: str  # "maintenance" | "weight_gain"
    updated_at: datetime = Field(
        default_factory=_utcnow, sa_column=Column(DateTime(timezone=True), nullable=False)
    )
