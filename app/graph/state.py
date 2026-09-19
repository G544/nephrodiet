import operator
from typing import Annotated, TypedDict

from app.domain.schemas import (
    CalorieTargetInput,
    DayResult,
    DaySkeleton,
    ProfileInput,
    WeekReview,
    WeekSkeleton,
)


class GenerationState(TypedDict, total=False):
    profile: ProfileInput
    preferences: list[str]
    calorie_target: CalorieTargetInput

    week_skeleton: WeekSkeleton
    day_results: Annotated[list[DayResult], operator.add]
    review: WeekReview


class RefineDayInput(TypedDict):
    """Payload dispatched to each parallel `refine_day` branch via `Send`."""

    day: DaySkeleton
    profile: ProfileInput
    calorie_target: CalorieTargetInput
