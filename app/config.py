from functools import lru_cache
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

# libpq-style query params that asyncpg does not understand (it takes `ssl=` instead).
_LIBPQ_ONLY_PARAMS = ("sslmode", "channel_binding")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Any Postgres URL: `postgresql://...` as copied from the Neon console works as-is.
    database_url: str = "postgresql://postgres:nephrodiet@localhost:5432/nephrodiet"

    gemini_api_key: str = ""
    gemini_model_stage1: str = "gemini-2.5-flash"
    gemini_model_stage2: str = "gemini-2.5-flash-lite"
    gemini_model_stage3: str = "gemini-2.5-flash"

    # Optional shared password for the Streamlit UI; empty = no gate.
    app_password: str = ""

    weight_gain_surplus: float = 1.125
    calorie_ceiling_ratio: float = 1.2

    @property
    def sync_database_url(self) -> str:
        """URL for psycopg (Alembic). libpq params like sslmode/channel_binding pass through."""
        url = make_url(self.database_url).set(drivername="postgresql+psycopg")
        return url.render_as_string(hide_password=False)

    @property
    def async_database_url(self) -> str:
        """URL for asyncpg, with libpq-only params removed (see async_connect_args)."""
        url = make_url(self.database_url).set(drivername="postgresql+asyncpg")
        url = url.difference_update_query(_LIBPQ_ONLY_PARAMS)
        return url.render_as_string(hide_password=False)

    @property
    def async_connect_args(self) -> dict[str, Any]:
        """asyncpg connect args translated from the URL's sslmode.

        statement_cache_size=0 keeps asyncpg working through Neon's pgbouncer pooler."""
        sslmode = make_url(self.database_url).query.get("sslmode", "prefer")
        args: dict[str, Any] = {"statement_cache_size": 0}
        if sslmode in ("require", "verify-ca", "verify-full"):
            args["ssl"] = True
        return args


@lru_cache
def get_settings() -> Settings:
    return Settings()
