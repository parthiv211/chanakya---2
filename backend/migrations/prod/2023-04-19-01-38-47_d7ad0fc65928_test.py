"""test

Revision ID: d7ad0fc65928
Revises: 618756b63ff9
Create Date: 2023-04-19 01:38:47.207685

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'd7ad0fc65928'
down_revision = '618756b63ff9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user', 'department')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('department', sa.INTEGER(), autoincrement=False, nullable=True))
    # ### end Alembic commands ###
