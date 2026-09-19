from functools import lru_cache
from typing import Literal

from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import get_settings

Stage = Literal["stage1", "stage2", "stage3"]


@lru_cache
def get_llm(stage: Stage) -> ChatGoogleGenerativeAI:
    settings = get_settings()
    model_by_stage = {
        "stage1": settings.gemini_model_stage1,
        "stage2": settings.gemini_model_stage2,
        "stage3": settings.gemini_model_stage3,
    }
    return ChatGoogleGenerativeAI(
        model=model_by_stage[stage],
        google_api_key=settings.gemini_api_key,
        temperature=0.7,
    )
