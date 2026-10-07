"""Initial schema for the first operational increment.

Revision ID: 0001_initial
Revises:
"""

from alembic import op

import app.infrastructure.models  # noqa: F401
from app.infrastructure.database import Base

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Keep this baseline aligned with the declarative model; follow-up changes use explicit diffs.
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
