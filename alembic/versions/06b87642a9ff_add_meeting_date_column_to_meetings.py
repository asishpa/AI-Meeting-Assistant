"""add meeting_date column to meetings

Revision ID: 06b87642a9ff
Revises: 8a061db39490
Create Date: 2025-09-27 10:16:31.659976
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '06b87642a9ff'
down_revision = '8a061db39490'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add meeting_date column to existing meetings table
    op.add_column(
        'meetings',
        sa.Column('meeting_date', sa.Date(), server_default=sa.text('CURRENT_DATE'), nullable=True),
        schema='assistant'
    )


def downgrade() -> None:
    # Remove the meeting_date column
    op.drop_column('meetings', 'meeting_date', schema='assistant')
