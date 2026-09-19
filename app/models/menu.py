from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(UTC)


class WeeklyMenu(SQLModel, table=True):
    __tablename__ = "weekly_menus"

    id: int | None = Field(default=None, primary_key=True)
    week_start_date: date
    status: str = "generating"  # "generating" | "final" | "error"

    calorie_target_kcal: float
    calorie_target_min: float
    calorie_target_max: float

    profile_snapshot: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB))

    review_status: str = "ok"  # "ok" | "warning"
    review_summary_ru: str = ""

    created_at: datetime = Field(
        default_factory=_utcnow, sa_column=Column(DateTime(timezone=True), nullable=False)
    )


class MenuDay(SQLModel, table=True):
    __tablename__ = "menu_days"

    id: int | None = Field(default=None, primary_key=True)
    weekly_menu_id: int = Field(foreign_key="weekly_menus.id")
    day_index: int
    date: date

    breakfast_recipe_id: int = Field(foreign_key="recipe.id")
    lunch_recipe_id: int = Field(foreign_key="recipe.id")
    dinner_recipe_id: int = Field(foreign_key="recipe.id")

    # Per-meal snapshot as served this day: {"breakfast": {"scale_factor", "ingredients",
    # "calories_kcal", "protein_g", "salt_g", "fat_g", "carbs_g"}, "lunch": {...}, "dinner": {...}}.
    # A day's serving may be scaled up from the canonical library recipe to hit the calorie
    # floor, so it's tracked here rather than mutating the shared `recipe` row.
    meals: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB))

    # Per-serving (what the patient actually eats in a day), not the whole-dish totals.
    total_calories_kcal: float
    total_protein_g: float
    total_salt_g: float
    total_fat_g: float
    total_carbs_g: float
    total_potassium_mg: float = 0.0
    total_phosphorus_mg: float = 0.0

    adjustment_notes: str = ""


class MenuWarning(SQLModel, table=True):
    __tablename__ = "menu_warnings"

    id: int | None = Field(default=None, primary_key=True)
    weekly_menu_id: int = Field(foreign_key="weekly_menus.id")
    day_index: int | None = None  # None = week-wide warning
    metric: str
    severity: str  # "info" | "warning"
    message_ru: str
