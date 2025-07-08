"""create_news_feeds_and_articles_tables

Revision ID: 19ca9d0b2b16
Revises: a36061e28468
Create Date: 2025-06-30 12:33:19.438280

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '19ca9d0b2b16'
down_revision: Union[str, Sequence[str], None] = 'a36061e28468'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create news_articles table
    op.create_table(
        'news_articles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('published_at', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(255), nullable=False),
        sa.Column('raw_html_path', sa.Text(), nullable=True),
        sa.Column('content_markdown_path', sa.Text(), nullable=True),
        sa.Column('thumbnail_url', sa.Text(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('summary_short', sa.Text(), nullable=True),
        sa.Column('keywords', sa.Text(), nullable=True),
        sa.Column('author', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_news_articles_id'), 'news_articles', ['id'], unique=False)
    op.create_index(op.f('ix_news_articles_url'), 'news_articles', ['url'], unique=True)
    op.create_index(op.f('ix_news_articles_source'), 'news_articles', ['source'], unique=False)
    
    # Create news_feeds table
    op.create_table(
        'news_feeds',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('query_prompt', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_news_feeds_id'), 'news_feeds', ['id'], unique=False)
    op.create_index(op.f('ix_news_feeds_user_id'), 'news_feeds', ['user_id'], unique=False)
    
    # Create news_feed_items table
    op.create_table(
        'news_feed_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('news_feed_id', sa.Integer(), nullable=False),
        sa.Column('news_article_id', sa.Integer(), nullable=False),
        sa.Column('curation_scores', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['news_article_id'], ['news_articles.id'], ),
        sa.ForeignKeyConstraint(['news_feed_id'], ['news_feeds.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_news_feed_items_id'), 'news_feed_items', ['id'], unique=False)
    op.create_index(op.f('ix_news_feed_items_news_feed_id'), 'news_feed_items', ['news_feed_id'], unique=False)
    op.create_index(op.f('ix_news_feed_items_news_article_id'), 'news_feed_items', ['news_article_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop news_feed_items table
    op.drop_index(op.f('ix_news_feed_items_news_article_id'), table_name='news_feed_items')
    op.drop_index(op.f('ix_news_feed_items_news_feed_id'), table_name='news_feed_items')
    op.drop_index(op.f('ix_news_feed_items_id'), table_name='news_feed_items')
    op.drop_table('news_feed_items')
    
    # Drop news_feeds table
    op.drop_index(op.f('ix_news_feeds_user_id'), table_name='news_feeds')
    op.drop_index(op.f('ix_news_feeds_id'), table_name='news_feeds')
    op.drop_table('news_feeds')
    
    # Drop news_articles table
    op.drop_index(op.f('ix_news_articles_source'), table_name='news_articles')
    op.drop_index(op.f('ix_news_articles_url'), table_name='news_articles')
    op.drop_index(op.f('ix_news_articles_id'), table_name='news_articles')
    op.drop_table('news_articles')
