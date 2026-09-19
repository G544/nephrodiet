"""Bridge between Streamlit's synchronous reruns and the async services/LangGraph pipeline.

Streamlit re-executes the script in a fresh thread on every interaction, but asyncpg
connections and LangChain clients are bound to the event loop that created them. So all
async work runs on one long-lived loop in a background thread, and the engine's connection
pool is reused across reruns.
"""

import asyncio
import contextlib
import os
import threading
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

import streamlit as st

T = TypeVar("T")

_SECRET_KEYS = (
    "DATABASE_URL",
    "GEMINI_API_KEY",
    "GEMINI_MODEL_STAGE1",
    "GEMINI_MODEL_STAGE2",
    "GEMINI_MODEL_STAGE3",
    "APP_PASSWORD",
)


def load_secrets_into_env() -> None:
    """Expose Streamlit secrets (Community Cloud UI or .streamlit/secrets.toml) to
    pydantic-settings, which reads plain environment variables. Must run before app.config
    settings are first read. A local .env still works when no secrets exist."""
    with contextlib.suppress(FileNotFoundError):  # no secrets file: use .env / environment
        for key in _SECRET_KEYS:
            if key in st.secrets:
                os.environ.setdefault(key, str(st.secrets[key]))


load_secrets_into_env()


@st.cache_resource
def _loop() -> asyncio.AbstractEventLoop:
    loop = asyncio.new_event_loop()
    threading.Thread(target=loop.run_forever, name="nephrodiet-async", daemon=True).start()
    return loop


def run_async(coro: Awaitable[T]) -> T:
    return asyncio.run_coroutine_threadsafe(coro, _loop()).result()  # type: ignore[arg-type]


def run_db(fn: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any) -> T:
    """Call `fn(session, *args, **kwargs)` in its own session and commit afterwards."""
    from app.db.session import async_session_factory

    async def job() -> T:
        async with async_session_factory() as session:
            result = await fn(session, *args, **kwargs)
            await session.commit()
            return result

    return run_async(job())
