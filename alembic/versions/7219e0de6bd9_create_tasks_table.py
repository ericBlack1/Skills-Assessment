"""create tasks table

Revision ID: 7219e0de6bd9
Revises: 
Create Date: 2026-09-24 01:11:08.049392

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7219e0de6bd9'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

task_status = sa.Enum('todo', 'in-progress', 'done', name='task_status')


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('tasks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('status', task_status, server_default='todo', nullable=False),
    sa.Column('due_date', sa.Date(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('tasks')
    # drop_table leaves the PostgreSQL enum type behind, which would make a
    # subsequent upgrade fail with "type task_status already exists".
    task_status.drop(op.get_bind())
