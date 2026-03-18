"""Add notes to customer

Revision ID: c291c07834a2
Revises: 75966e4fa446
Create Date: 2026-03-18 16:13:36.970377

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c291c07834a2'
down_revision: Union[str, Sequence[str], None] = '75966e4fa446'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('customers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('marketing_opt_in', sa.Boolean(), server_default='1', nullable=True))

def downgrade() -> None:
    with op.batch_alter_table('customers', schema=None) as batch_op:
        batch_op.drop_column('marketing_opt_in')
