from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Recipe(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    normalized_name: str = Field(index=True)
    description: str = ""
    instructions: str

    meal_slots: list[str] = Field(default_factory=list, sa_column=Column(ARRAY(String)))
    dish_type: str
    protein_type: str
    tags: list[str] = Field(default_factory=list, sa_column=Column(ARRAY(String)))

    servings: int = 2
    ingredients: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSONB))

    # Whole-dish (all servings) totals — see app/graph/nodes.py::_per_serving for the
    # per-serving amount actually eaten.
    calories_kcal: float
    protein_g: float
    salt_g: float
    fat_g: float
    carbs_g: float
    potassium_mg: float = 0.0
    phosphorus_mg: float = 0.0

    usage_count: int = 0
    last_used_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    source: str = "generated"  # "generated" | "manual"

    created_at: datetime = Field(
        default_factory=_utcnow, sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=_utcnow, sa_column=Column(DateTime(timezone=True), nullable=False)
    )
