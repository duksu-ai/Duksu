"""Create news source mapping and query execution tables

Revision ID: a36061e28468
Revises: 
Create Date: 2025-06-28 15:44:01.619555

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a36061e28468'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create news_source_mappings table
    op.create_table(
        'news_source_mappings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('query_prompt', sa.Text(), nullable=False),
        sa.Column('selected_sources', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_news_source_mappings_id'), 'news_source_mappings', ['id'], unique=False)
    op.create_index(op.f('ix_news_source_mappings_user_id'), 'news_source_mappings', ['user_id'], unique=False)
    
    # Create workflow_run_history table
    op.create_table(
        'workflow_run_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workflow_name', sa.String(255), nullable=False),
        sa.Column('input_data', sa.Text(), nullable=False),
        sa.Column('output_data', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('started', 'completed', 'failed', 'error', name='workflowrunstatus'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workflow_run_history_id'), 'workflow_run_history', ['id'], unique=False)
    op.create_index(op.f('ix_workflow_run_history_workflow_name'), 'workflow_run_history', ['workflow_name'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop workflow_run_history table
    op.drop_index(op.f('ix_workflow_run_history_workflow_name'), table_name='workflow_run_history')
    op.drop_index(op.f('ix_workflow_run_history_id'), table_name='workflow_run_history')
    op.drop_table('workflow_run_history')
    
    # Drop news_source_mappings table
    op.drop_index(op.f('ix_news_source_mappings_user_id'), table_name='news_source_mappings')
    op.drop_index(op.f('ix_news_source_mappings_id'), table_name='news_source_mappings')
    op.drop_table('news_source_mappings')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS workflowrunstatus')
