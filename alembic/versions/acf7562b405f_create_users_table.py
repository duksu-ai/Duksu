"""create_users_table

Revision ID: acf7562b405f
Revises: 19ca9d0b2b16
Create Date: 2025-06-30 16:21:51.962194

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'acf7562b405f'
down_revision: Union[str, Sequence[str], None] = '19ca9d0b2b16'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_user_id'), 'users', ['user_id'], unique=True)
    
    # Add foreign key constraint to news_feeds table
    op.create_foreign_key(
        constraint_name='fk_news_feeds_user_id',
        source_table='news_feeds',
        referent_table='users',
        local_cols=['user_id'],
        remote_cols=['user_id']
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop foreign key constraint from news_feeds table
    op.drop_constraint('fk_news_feeds_user_id', 'news_feeds', type_='foreignkey')
    
    # Drop users table
    op.drop_index(op.f('ix_users_user_id'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
