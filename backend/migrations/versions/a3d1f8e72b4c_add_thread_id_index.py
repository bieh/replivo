"""add index on conversations.agentmail_thread_id

Revision ID: a3d1f8e72b4c
Revises: 66bb74b53ffb
Create Date: 2026-02-14 18:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'a3d1f8e72b4c'
down_revision = '66bb74b53ffb'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('conversations', schema=None) as batch_op:
        batch_op.create_index('ix_conversation_thread_id', ['agentmail_thread_id'])


def downgrade():
    with op.batch_alter_table('conversations', schema=None) as batch_op:
        batch_op.drop_index('ix_conversation_thread_id')
