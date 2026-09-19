from typing import Literal

from app.config import get_settings

Sex = Literal["male", "female"]
ActivityLevel = Literal["sedentary", "light", "moderate", "active"]
Goal = Literal["maintenance", "weight_gain"]

PAL: dict[ActivityLevel, float] = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
}


def per_serving(value: float, servings: int) -> float:
    """A recipe's nutrition fields (calories/protein/salt/fat/carbs/potassium/phosphorus)
    are always WHOLE-DISH totals (all servings combined) — the patient eats exactly one
    serving, so this is what they actually consume. Used both when aggregating a day's
    totals and when displaying a single recipe's per-serving nutrition."""
    return value / servings if servings else value


def bmr_mifflin_st_jeor(weight_kg: float, height_cm: float, age: int, sex: Sex) -> float:
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + 5 if sex == "male" else base - 161


def tdee(weight_kg: float, height_cm: float, age: int, sex: Sex, activity_level: ActivityLevel) -> float:
    return bmr_mifflin_st_jeor(weight_kg, height_cm, age, sex) * PAL[activity_level]


class CalorieTarget:
    def __init__(self, target_kcal: float, min_kcal: float, max_kcal: float) -> None:
        self.target_kcal = target_kcal
        self.min_kcal = min_kcal
        self.max_kcal = max_kcal

    def __repr__(self) -> str:  # pragma: no cover
        return f"CalorieTarget(target={self.target_kcal:.0f}, min={self.min_kcal:.0f}, max={self.max_kcal:.0f})"


def calculate_calorie_target(
    weight_kg: float,
    height_cm: float,
    age: int,
    sex: Sex,
    activity_level: ActivityLevel,
    goal: Goal,
) -> CalorieTarget:
    settings = get_settings()
    energy = tdee(weight_kg, height_cm, age, sex, activity_level)
    target = energy if goal == "maintenance" else energy * settings.weight_gain_surplus
    return CalorieTarget(
        target_kcal=target,
        min_kcal=target,
        max_kcal=target * settings.calorie_ceiling_ratio,
    )
