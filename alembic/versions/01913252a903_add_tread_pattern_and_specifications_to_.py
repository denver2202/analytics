"""Add tread_pattern and specifications to products

Revision ID: 01913252a903
Revises: e51a3d7cf080
Create Date: 2025-11-02 23:33:43.921870

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '01913252a903'
down_revision: Union[str, None] = 'e51a3d7cf080'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавляем поле типа протектора
    op.add_column('products', sa.Column('tread_pattern', sa.String(length=64), nullable=True))
    op.create_index(op.f('ix_products_tread_pattern'), 'products', ['tread_pattern'], unique=False)
    
    # Добавляем поле для характеристик (JSON в виде строки)
    op.add_column('products', sa.Column('specifications', sa.String(length=2048), nullable=True))


def downgrade() -> None:
    # Удаляем индексы и колонки в обратном порядке
    op.drop_index(op.f('ix_products_tread_pattern'), table_name='products')
    op.drop_column('products', 'specifications')
    op.drop_column('products', 'tread_pattern')
