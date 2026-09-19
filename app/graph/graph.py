from langgraph.graph import END, START, StateGraph

from app.domain.schemas import (
    CalorieTargetInput,
    ProfileInput,
    WeekReview,
)
from app.graph.nodes import build_skeleton, dispatch_days, refine_day, review_week
from app.graph.state import GenerationState, RefineDayInput


def build_graph():
    graph = StateGraph(GenerationState)
    graph.add_node("build_skeleton", build_skeleton)
    graph.add_node("refine_day", refine_day, input_schema=RefineDayInput)
    graph.add_node("review_week", review_week)

    graph.add_edge(START, "build_skeleton")
    graph.add_conditional_edges("build_skeleton", dispatch_days, ["refine_day"])
    graph.add_edge("refine_day", "review_week")
    graph.add_edge("review_week", END)

    return graph.compile()


_compiled_graph = None


def get_compiled_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


class WeekGenerationResult:
    def __init__(self, week_skeleton, day_results, review: WeekReview) -> None:
        self.week_skeleton = week_skeleton
        self.day_results = day_results
        self.review = review


async def generate_week(
    profile: ProfileInput,
    preferences: list[str],
    calorie_target: CalorieTargetInput,
) -> WeekGenerationResult:
    """Pure orchestration entrypoint: no DB access happens inside the graph itself —
    callers persist the result afterwards. Every recipe is always generated from scratch
    by the LLM (no reuse-from-library shortcut) — see app/graph/nodes.py::refine_day."""
    graph = get_compiled_graph()
    result = await graph.ainvoke(
        {
            "profile": profile,
            "preferences": preferences,
            "calorie_target": calorie_target,
        }
    )
    day_results = sorted(result["day_results"], key=lambda d: d.day_index)
    return WeekGenerationResult(
        week_skeleton=result["week_skeleton"],
        day_results=day_results,
        review=result["review"],
    )
