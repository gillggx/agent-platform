"""add codebase_path to projects

Revision ID: 002
Revises: 001
Create Date: 2026-03-19
"""
from alembic import op
import sqlalchemy as sa

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('projects', sa.Column('codebase_path', sa.String(1000), nullable=True))


def downgrade():
    op.drop_column('projects', 'codebase_path')
