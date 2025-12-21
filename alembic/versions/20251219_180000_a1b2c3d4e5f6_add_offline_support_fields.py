"""Add offline support fields to scores table

Revision ID: a1b2c3d4e5f6
Revises: 539d94d4f5e3
Create Date: 2025-12-19 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '539d94d4f5e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add played_at column for client-provided timestamps (offline games)
    op.add_column('scores', sa.Column('played_at', sa.DateTime(timezone=True), nullable=True))

    # Add idempotency_key column for preventing duplicate submissions
    op.add_column('scores', sa.Column('idempotency_key', sa.String(64), nullable=True))

    # Create partial unique index on idempotency_key (only when not null)
    op.create_index(
        'ix_scores_idempotency_key',
        'scores',
        ['idempotency_key'],
        unique=True,
        postgresql_where=sa.text('idempotency_key IS NOT NULL')
    )


def downgrade() -> None:
    op.drop_index('ix_scores_idempotency_key', table_name='scores')
    op.drop_column('scores', 'idempotency_key')
    op.drop_column('scores', 'played_at')
