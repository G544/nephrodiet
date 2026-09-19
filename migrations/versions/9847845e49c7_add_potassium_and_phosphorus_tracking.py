"""add potassium and phosphorus tracking

Revision ID: 9847845e49c7
Revises: ac6a3278f8b8
Create Date: 2026-09-18 15:29:50.378796

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '9847845e49c7'
down_revision: Union[str, Sequence[str], None] = 'ac6a3278f8b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # server_default='0' backfills existing rows (already-generated recipes/menu days
    # predate potassium/phosphorus tracking, so there is no real historical value for them).
    # NOTE: autogenerate also proposed dropping recipe_normalized_name_trgm_idx — that's a
    # raw-SQL trigram index (migration bd426b9a27fb) not represented in SQLModel.metadata,
    # so autogenerate sees it as "extra" and wants to remove it. It's still needed by
    # app/domain/recipe_dedup.py's fuzzy name search, so that op is intentionally omitted.
    op.add_column('menu_days', sa.Column('total_potassium_mg', sa.Float(), nullable=False, server_default='0'))
    op.add_column('menu_days', sa.Column('total_phosphorus_mg', sa.Float(), nullable=False, server_default='0'))
    op.add_column('recipe', sa.Column('potassium_mg', sa.Float(), nullable=False, server_default='0'))
    op.add_column('recipe', sa.Column('phosphorus_mg', sa.Float(), nullable=False, server_default='0'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('recipe', 'phosphorus_mg')
    op.drop_column('recipe', 'potassium_mg')
    op.drop_column('menu_days', 'total_phosphorus_mg')
    op.drop_column('menu_days', 'total_potassium_mg')
