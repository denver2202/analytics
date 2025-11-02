"""Initial migration: create tables

Revision ID: e51a3d7cf080
Revises: 
Create Date: 2025-11-02 23:23:53.567015

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e51a3d7cf080'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Создаем таблицу products
    op.create_table(
        'products',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sku', sa.String(length=64), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=128), nullable=True),
        sa.Column('url', sa.String(length=512), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_products_sku'), 'products', ['sku'], unique=True)
    
    # Создаем таблицу price_snapshots
    op.create_table(
        'price_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('in_stock', sa.Boolean(), nullable=True),
        sa.Column('promo', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('product_id', 'date', name='uq_ps_prod_date')
    )
    op.create_index(op.f('ix_price_snapshots_date'), 'price_snapshots', ['date'], unique=False)
    
    # Создаем таблицу traffic_metrics
    op.create_table(
        'traffic_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('region', sa.String(length=64), nullable=True),
        sa.Column('metric_name', sa.String(length=64), nullable=True),
        sa.Column('value', sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_traffic_metrics_date'), 'traffic_metrics', ['date'], unique=False)
    op.create_index(op.f('ix_traffic_metrics_metric_name'), 'traffic_metrics', ['metric_name'], unique=False)
    
    # Создаем таблицу forecasts
    op.create_table(
        'forecasts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('yhat', sa.Float(), nullable=False),
        sa.Column('yhat_lower', sa.Float(), nullable=True),
        sa.Column('yhat_upper', sa.Float(), nullable=True),
        sa.Column('model_version', sa.String(length=32), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_forecasts_date'), 'forecasts', ['date'], unique=False)


def downgrade() -> None:
    # Удаляем таблицы в обратном порядке (сначала те, что имеют внешние ключи)
    op.drop_index(op.f('ix_forecasts_date'), table_name='forecasts')
    op.drop_table('forecasts')
    
    op.drop_index(op.f('ix_traffic_metrics_metric_name'), table_name='traffic_metrics')
    op.drop_index(op.f('ix_traffic_metrics_date'), table_name='traffic_metrics')
    op.drop_table('traffic_metrics')
    
    op.drop_index(op.f('ix_price_snapshots_date'), table_name='price_snapshots')
    op.drop_table('price_snapshots')
    
    op.drop_index(op.f('ix_products_sku'), table_name='products')
    op.drop_table('products')
