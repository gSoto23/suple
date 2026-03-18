"""Add marketing tables

Revision ID: cf2d6e4e6047
Revises: c291c07834a2
Create Date: 2026-03-18 16:15:04.214864

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cf2d6e4e6047'
down_revision: Union[str, Sequence[str], None] = 'c291c07834a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('marketing_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('language', sa.String(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('components', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('marketing_templates', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_marketing_templates_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_marketing_templates_name'), ['name'], unique=True)

    op.create_table('campaigns',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('variables_mapping', sa.JSON(), nullable=True),
        sa.Column('scheduled_at', sa.DateTime(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['template_id'], ['marketing_templates.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('campaigns', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_campaigns_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_campaigns_name'), ['name'], unique=False)

    op.create_table('campaign_recipients',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('campaign_id', sa.Integer(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('message_id', sa.String(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('campaign_recipients', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_campaign_recipients_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_campaign_recipients_message_id'), ['message_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_campaign_recipients_status'), ['status'], unique=False)

def downgrade() -> None:
    with op.batch_alter_table('campaign_recipients', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_campaign_recipients_status'))
        batch_op.drop_index(batch_op.f('ix_campaign_recipients_message_id'))
        batch_op.drop_index(batch_op.f('ix_campaign_recipients_id'))
    op.drop_table('campaign_recipients')

    with op.batch_alter_table('campaigns', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_campaigns_name'))
        batch_op.drop_index(batch_op.f('ix_campaigns_id'))
    op.drop_table('campaigns')

    with op.batch_alter_table('marketing_templates', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_marketing_templates_name'))
        batch_op.drop_index(batch_op.f('ix_marketing_templates_id'))
    op.drop_table('marketing_templates')
