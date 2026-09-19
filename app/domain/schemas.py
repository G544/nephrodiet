from typing import Literal

from pydantic import BaseModel, Field

MealSlot = Literal["breakfast", "lunch", "dinner"]


class ProfileInput(BaseModel):
    age: int
    weight_kg: float
    height_cm: float
    sex: Literal["male", "female"]
    activity_level: Literal["sedentary", "light", "moderate", "active"]
    egfr: float = 0.0
    salt_limit_g: float
    protein_limit_g: float
    goal: Literal["maintenance", "weight_gain"]


class CalorieTargetInput(BaseModel):
    target_kcal: float
    min_kcal: float
    max_kcal: float


# ---- Stage 1: weekly skeleton ----


class DayPlanSlot(BaseModel):
    meal_slot: MealSlot
    recipe_name: str
    short_description: str
    dish_type: str
    protein_type: str


class DaySkeleton(BaseModel):
    day_index: int
    weekday_name_ru: str
    breakfast: DayPlanSlot
    lunch: DayPlanSlot
    dinner: DayPlanSlot


class WeekSkeleton(BaseModel):
    days: list[DaySkeleton]


# ---- Stage 2: per-day refinement ----


class Ingredient(BaseModel):
    name: str
    amount_g: float
    unit: str
    note: str = ""


class IngredientWithNutrients(Ingredient):
    """Nutrient contribution of THIS ingredient at its amount_g in the dish. Requiring this
    per ingredient (rather than asking the LLM for one holistic dish-level total) is what
    prevents the LLM from silently forgetting a component's contribution — e.g. counting a
    fish fillet's protein but forgetting the pasta it's served with — since Python sums
    these into the dish total rather than trusting a single top-down estimate."""

    calories_kcal: float
    protein_g: float
    salt_g: float
    fat_g: float
    carbs_g: float
    potassium_mg: float
    phosphorus_mg: float


class NewRecipeDraft(BaseModel):
    """LLM structured-output shape for a freshly invented recipe. Deliberately has NO
    dish-level nutrition fields — those are computed in app/graph/nodes.py by summing
    `ingredients`, rather than asked of the LLM directly."""

    name: str
    meal_slot: MealSlot
    servings: int = 2
    ingredients: list[IngredientWithNutrients]
    instructions: str
    dish_type: str
    protein_type: str


class FinalizedRecipe(BaseModel):
    name: str
    meal_slot: MealSlot
    servings: int = 2
    ingredients: list[IngredientWithNutrients]
    instructions: str
    dish_type: str
    protein_type: str
    # All nutrition fields below are for the WHOLE dish (all servings combined), not per
    # serving — see app/graph/nodes.py::_per_serving for where the per-serving amount the
    # patient actually eats is derived from these. They are computed as the sum of
    # `ingredients`' own nutrient fields, not LLM-supplied directly — see
    # app/graph/nodes.py::_finalize_recipe_from_draft.
    calories_kcal: float
    protein_g: float
    salt_g: float
    fat_g: float
    carbs_g: float
    potassium_mg: float
    phosphorus_mg: float


class DayResult(BaseModel):
    day_index: int
    breakfast: FinalizedRecipe
    lunch: FinalizedRecipe
    dinner: FinalizedRecipe
    # Per-serving (i.e. what the patient actually eats in a day) — see
    # app/graph/nodes.py::refine_day.
    total_calories_kcal: float
    total_protein_g: float
    total_salt_g: float
    total_fat_g: float
    total_carbs_g: float
    total_potassium_mg: float
    total_phosphorus_mg: float
    adjustment_notes: str = ""


# ---- Stage 3: week review ----


class WarningFlag(BaseModel):
    day_index: int = Field(description="-1 for a week-wide warning")
    metric: str
    severity: Literal["info", "warning"]
    message_ru: str


class WeekReview(BaseModel):
    is_within_limits: bool
    summary_ru: str
    flags: list[WarningFlag] = Field(default_factory=list)
