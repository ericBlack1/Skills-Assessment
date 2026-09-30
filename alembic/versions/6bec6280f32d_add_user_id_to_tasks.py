"""add user_id to tasks

Revision ID: 6bec6280f32d
Revises: 298c983704ef
Create Date: 2026-09-26 01:59:39.745718

Existing tasks without an owner cannot be assigned reliably, so they are removed
before adding the required user_id foreign key.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6bec6280f32d"
down_revision: Union[str, Sequence[str], None] = "298c983704ef"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("DELETE FROM tasks")
    op.add_column("tasks", sa.Column("user_id", sa.Integer(), nullable=False))
    op.create_index("ix_tasks_user_id", "tasks", ["user_id"], unique=False)
    op.create_foreign_key(
        "fk_tasks_user_id_users",
        "tasks",
        "users",
        ["user_id"],
        ["id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("fk_tasks_user_id_users", "tasks", type_="foreignkey")
    op.drop_index("ix_tasks_user_id", table_name="tasks")
    op.drop_column("tasks", "user_id")
