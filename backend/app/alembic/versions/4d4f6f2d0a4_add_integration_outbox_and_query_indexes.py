"""add integration tables, outbox, idempotency and query indexes

Revision ID: 4d4f6f2d0a4
Revises: 232ae510c217
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "4d4f6f2d0a4"
down_revision = "232ae510c217"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "machine_api_key",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("client_name", sa.String(length=120), nullable=False),
        sa.Column("key_id", sa.String(length=80), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("scopes", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_id"),
    )
    op.create_index("ix_machine_api_key_key_id", "machine_api_key", ["key_id"], unique=False)
    op.create_index("machine_api_key_hash_idx", "machine_api_key", ["key_hash"], unique=True)
    op.create_index("machine_api_key_active_idx", "machine_api_key", ["active", "expires_at"], unique=False)

    op.create_table(
        "outbox_message",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("aggregate_type", sa.String(length=80), nullable=False),
        sa.Column("aggregate_id", sa.String(length=120), nullable=False),
        sa.Column("payload", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dead_lettered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_outbox_message_available_at", "outbox_message", ["available_at"], unique=False)
    op.create_index("ix_outbox_message_delivered_at", "outbox_message", ["delivered_at"], unique=False)
    op.create_index("outbox_available_idx", "outbox_message", ["available_at", "delivered_at", "dead_lettered_at"], unique=False)
    op.create_index("outbox_event_type_idx", "outbox_message", ["event_type", "created_at"], unique=False)

    op.create_table(
        "idempotency_record",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scope", sa.String(length=160), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("response_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scope", "key", name="uq_idempotency_scope_key"),
    )
    op.create_index("idempotency_expires_idx", "idempotency_record", ["expires_at"], unique=False)
    op.create_index("ix_idempotency_record_expires_at", "idempotency_record", ["expires_at"], unique=False)

    op.create_index("instrument_maturity_idx", "instrument", ["maturity_date", "lifecycle"], unique=False)
    op.create_index(
        "instrument_active_region_idx",
        "instrument",
        ["region", "maturity_date"],
        unique=False,
        postgresql_where=sa.text("lifecycle IN ('pending','active','matured','renewed')"),
    )
    op.create_index("confirmation_status_idx", "confirmation", ["instrument_id", "status", "confirmed_at"], unique=False)
    op.create_index("obligation_open_due_idx", "obligation", ["due_date", "owner_role"], unique=False, postgresql_where=sa.text("status = 'open'"))
    op.create_index("notice_instrument_sent_idx", "notice", ["instrument_id", "sent_at"], unique=False)
    op.create_index("case_note_instrument_created_idx", "case_note", ["instrument_id", "created_at"], unique=False)
    op.create_index("flag_waiver_instrument_code_idx", "flag_waiver", ["instrument_id", "code"], unique=False)
    op.create_index("release_request_status_idx", "release_request", ["status", "updated_at"], unique=False)


def downgrade() -> None:
    for name, table in (
        ("release_request_status_idx", "release_request"),
        ("flag_waiver_instrument_code_idx", "flag_waiver"),
        ("case_note_instrument_created_idx", "case_note"),
        ("notice_instrument_sent_idx", "notice"),
        ("obligation_open_due_idx", "obligation"),
        ("confirmation_status_idx", "confirmation"),
        ("instrument_active_region_idx", "instrument"),
        ("instrument_maturity_idx", "instrument"),
    ):
        op.drop_index(name, table_name=table)
    op.drop_table("idempotency_record")
    op.drop_table("outbox_message")
    op.drop_table("machine_api_key")
