"""add margin tax fields to sale_line_item and artwork_consignment

Revision ID: a1b2c3d4e5f6
Revises: c91e23e69dc1
Create Date: 2026-06-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = 'c91e23e69dc1'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('sale_line_item', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tax_method', sa.String(10),
                                      nullable=False, server_default='standard'))
        batch_op.add_column(sa.Column('purchase_price_at_sale',
                                      sa.Numeric(precision=12, scale=2), nullable=True))

    with op.batch_alter_table('artwork_consignment', schema=None) as batch_op:
        batch_op.add_column(sa.Column('purchase_price',
                                      sa.Numeric(precision=12, scale=2), nullable=True))
        batch_op.add_column(sa.Column('is_secondary_market',
                                      sa.Boolean(), nullable=False, server_default='false'))


def downgrade():
    with op.batch_alter_table('sale_line_item', schema=None) as batch_op:
        batch_op.drop_column('purchase_price_at_sale')
        batch_op.drop_column('tax_method')

    with op.batch_alter_table('artwork_consignment', schema=None) as batch_op:
        batch_op.drop_column('is_secondary_market')
        batch_op.drop_column('purchase_price')
