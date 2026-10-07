"""Distinguish inventory authorization from generic administrative affiliation.

Revision ID: 0002_inventory_admin
Revises: 0001_initial
"""

from alembic import op

revision = "0002_inventory_admin"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing installations keep PERSONAL_ADMINISTRATIVO identities; inventory
    # write permission now requires the explicit ADMIN_INVENTARIO role.
    op.execute("ALTER TYPE person_role ADD VALUE IF NOT EXISTS 'ADMIN_INVENTARIO'")
    op.execute("ALTER TYPE policy_role ADD VALUE IF NOT EXISTS 'ADMIN_INVENTARIO'")


def downgrade() -> None:
    # PostgreSQL 16 does not support dropping an enum label safely. The label is
    # inert after application code is downgraded and can remain in the type.
    pass
