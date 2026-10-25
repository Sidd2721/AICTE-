"""add rate limit bucket

Revision ID: 9bba68018f75
Revises: 9ec907551ae6
Create Date: 2026-10-25 17:21:49.621336

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = '9bba68018f75'
down_revision = '9ec907551ae6'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS rate_limit_bucket (
            key VARCHAR(255) PRIMARY KEY,
            count INTEGER NOT NULL DEFAULT 1,
            reset_at TIMESTAMPTZ NOT NULL
        );
        CREATE INDEX IF NOT EXISTS ix_rate_limit_bucket_reset_at ON rate_limit_bucket (reset_at);
        """
    )


def downgrade():
    op.execute("DROP TABLE IF EXISTS rate_limit_bucket CASCADE;")
