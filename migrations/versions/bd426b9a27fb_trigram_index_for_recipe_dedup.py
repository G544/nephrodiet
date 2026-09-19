"""trigram index for recipe dedup

Revision ID: bd426b9a27fb
Revises: 9c03bf3b0d52
Create Date: 2026-09-17 20:12:24.252036

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'bd426b9a27fb'
down_revision: Union[str, Sequence[str], None] = '9c03bf3b0d52'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX recipe_normalized_name_trgm_idx ON recipe "
        "USING gin (normalized_name gin_trgm_ops)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS recipe_normalized_name_trgm_idx")
