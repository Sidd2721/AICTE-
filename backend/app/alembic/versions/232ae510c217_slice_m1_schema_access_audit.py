"""slice_m1_schema_access_audit

Revision ID: 232ae510c217
Revises: 9bba68018f75
Create Date: 2026-10-25 17:38:17.755692

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '232ae510c217'
down_revision = '9bba68018f75'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Audit tables
    op.create_table(
        'audit_checkpoint',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('up_to_id', sa.BigInteger(), nullable=False),
        sa.Column('head_hash', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column('signature', sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'audit_event',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('ts', sa.DateTime(timezone=True), nullable=False),
        sa.Column('actor_id', sa.Uuid(), nullable=True),
        sa.Column('action', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column('entity', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column('entity_id', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('prev_hash', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column('hash', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_event_actor_id'), 'audit_event', ['actor_id'], unique=False)
    op.create_index(op.f('ix_audit_event_hash'), 'audit_event', ['hash'], unique=True)

    # 2. Institution table
    op.create_table(
        'institution',
        sa.Column('permanent_id', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column('region', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column('is_government', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('leased_private', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('programmes', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('contact_email', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_institution_permanent_id'), 'institution', ['permanent_id'], unique=True)
    op.create_index(op.f('ix_institution_region'), 'institution', ['region'], unique=False)

    # 3. Update User table
    op.add_column('user', sa.Column('role', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False, server_default='institution'))
    op.add_column('user', sa.Column('region', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True))
    op.add_column('user', sa.Column('institution_id', sa.Uuid(), nullable=True))
    op.create_foreign_key('fk_user_institution_id_institution', 'user', 'institution', ['institution_id'], ['id'])

    # 4. Instrument table
    op.create_table(
        'instrument',
        sa.Column('institution_id', sa.Uuid(), nullable=False),
        sa.Column('region', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column('kind', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column('ref_no', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column('bank_code', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column('ifsc', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column('amount_paise', sa.BigInteger(), nullable=False),
        sa.Column('issue_date', sa.Date(), nullable=False),
        sa.Column('maturity_date', sa.Date(), nullable=False),
        sa.Column('holders', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('lien_marked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_duplicate_receipt', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('lifecycle', sqlmodel.sql.sqltypes.AutoString(length=30), nullable=False, server_default='pending'),
        sa.Column('replaces_id', sa.Uuid(), nullable=True),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['created_by'], ['user.id'], ),
        sa.ForeignKeyConstraint(['institution_id'], ['institution.id'], ),
        sa.ForeignKeyConstraint(['replaces_id'], ['instrument.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("kind IN ('FDR','RTGS')", name="chk_instrument_kind"),
        sa.CheckConstraint("amount_paise > 0", name="chk_instrument_amount_paise"),
        sa.CheckConstraint("lifecycle IN ('pending','active','matured','renewed','released')", name="chk_instrument_lifecycle")
    )
    op.create_index(op.f('ix_instrument_institution_id'), 'instrument', ['institution_id'], unique=False)
    op.create_index(op.f('ix_instrument_region'), 'instrument', ['region'], unique=False)
    op.create_index('instrument_ref_idx', 'instrument', ['bank_code', 'ref_no'], unique=False)

    # 5. Case Note table
    op.create_table(
        'case_note',
        sa.Column('instrument_id', sa.Uuid(), nullable=False),
        sa.Column('author_id', sa.Uuid(), nullable=False),
        sa.Column('body', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['author_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['instrument_id'], ['instrument.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_case_note_author_id'), 'case_note', ['author_id'], unique=False)
    op.create_index(op.f('ix_case_note_instrument_id'), 'case_note', ['instrument_id'], unique=False)

    # 6. Document table
    op.create_table(
        'document',
        sa.Column('instrument_id', sa.Uuid(), nullable=False),
        sa.Column('kind', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('filename', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column('mime', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('sha256', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column('storage_key', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=False),
        sa.Column('uploaded_by', sa.Uuid(), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['instrument_id'], ['instrument.id'], ),
        sa.ForeignKeyConstraint(['uploaded_by'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('instrument_id', 'kind', 'version', name='uq_document_instrument_kind_version'),
        sa.CheckConstraint("version >= 1", name="chk_document_version"),
        sa.CheckConstraint("size_bytes > 0", name="chk_document_size_bytes")
    )
    op.create_index(op.f('ix_document_instrument_id'), 'document', ['instrument_id'], unique=False)
    op.create_index(op.f('ix_document_sha256'), 'document', ['sha256'], unique=False)

    # 7. Flag Waiver table
    op.create_table(
        'flag_waiver',
        sa.Column('instrument_id', sa.Uuid(), nullable=False),
        sa.Column('code', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column('reason', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('waived_by', sa.Uuid(), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['instrument_id'], ['instrument.id'], ),
        sa.ForeignKeyConstraint(['waived_by'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('instrument_id', 'code', name='uq_flag_waiver_instrument_code'),
        sa.CheckConstraint("length(reason) >= 10", name="chk_flag_waiver_reason_len")
    )
    op.create_index(op.f('ix_flag_waiver_instrument_id'), 'flag_waiver', ['instrument_id'], unique=False)

    # 8. Obligation table
    op.create_table(
        'obligation',
        sa.Column('instrument_id', sa.Uuid(), nullable=False),
        sa.Column('kind', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('status', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False, server_default='open'),
        sa.Column('owner_role', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.ForeignKeyConstraint(['instrument_id'], ['instrument.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('instrument_id', 'kind', 'due_date', name='uq_obligation_instrument_kind_due_date'),
        sa.CheckConstraint("status IN ('open','done','waived')", name="chk_obligation_status"),
        sa.CheckConstraint("owner_role IN ('institution','regional','bureau')", name="chk_obligation_owner_role")
    )
    op.create_index(op.f('ix_obligation_instrument_id'), 'obligation', ['instrument_id'], unique=False)

    # 9. Release Request table
    op.create_table(
        'release_request',
        sa.Column('instrument_id', sa.Uuid(), nullable=False),
        sa.Column('path', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column('checklist', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('status', sqlmodel.sql.sqltypes.AutoString(length=30), nullable=False, server_default='draft'),
        sa.Column('requested_by', sa.Uuid(), nullable=False),
        sa.Column('verified_by', sa.Uuid(), nullable=True),
        sa.Column('approved_by', sa.Uuid(), nullable=True),
        sa.Column('receipt_token', sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['approved_by'], ['user.id'], ),
        sa.ForeignKeyConstraint(['instrument_id'], ['instrument.id'], ),
        sa.ForeignKeyConstraint(['requested_by'], ['user.id'], ),
        sa.ForeignKeyConstraint(['verified_by'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("verified_by IS NULL OR approved_by IS NULL OR verified_by <> approved_by", name="chk_release_request_maker_checker"),
        sa.CheckConstraint("status IN ('draft','submitted','verified','approved','rejected','released')", name="chk_release_request_status")
    )
    op.create_index(op.f('ix_release_request_instrument_id'), 'release_request', ['instrument_id'], unique=False)

    # 10. Confirmation table
    op.create_table(
        'confirmation',
        sa.Column('instrument_id', sa.Uuid(), nullable=False),
        sa.Column('status', sqlmodel.sql.sqltypes.AutoString(length=30), nullable=False, server_default='requested'),
        sa.Column('method', sqlmodel.sql.sqltypes.AutoString(length=30), nullable=False),
        sa.Column('token_hash', sqlmodel.sql.sqltypes.AutoString(length=128), nullable=False),
        sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('token_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('fields', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('evidence_document_id', sa.Uuid(), nullable=True),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('id', sa.Uuid(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('requested_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['evidence_document_id'], ['document.id'], ),
        sa.ForeignKeyConstraint(['instrument_id'], ['instrument.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('requested','confirmed','rejected','unavailable')", name="chk_confirmation_status"),
        sa.CheckConstraint("method IN ('signed_letter','callback','manual')", name="chk_confirmation_method"),
        sa.CheckConstraint("status <> 'confirmed' OR (fields IS NOT NULL AND confirmed_at IS NOT NULL AND expires_at IS NOT NULL)", name="chk_confirmation_confirmed_fields")
    )
    op.create_index(op.f('ix_confirmation_instrument_id'), 'confirmation', ['instrument_id'], unique=False)
    op.create_index(op.f('ix_confirmation_token_hash'), 'confirmation', ['token_hash'], unique=False)

    # 11. Notice table
    op.create_table(
        'notice',
        sa.Column('instrument_id', sa.Uuid(), nullable=False),
        sa.Column('obligation_id', sa.Uuid(), nullable=False),
        sa.Column('step', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column('channel', sqlmodel.sql.sqltypes.AutoString(length=30), nullable=False, server_default='email'),
        sa.Column('delivered', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('id', sa.Uuid(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['instrument_id'], ['instrument.id'], ),
        sa.ForeignKeyConstraint(['obligation_id'], ['obligation.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('obligation_id', 'step', name='uq_notice_obligation_step')
    )
    op.create_index(op.f('ix_notice_instrument_id'), 'notice', ['instrument_id'], unique=False)
    op.create_index(op.f('ix_notice_obligation_id'), 'notice', ['obligation_id'], unique=False)

    # 12. Hardening & RLS Policies
    op.execute(
        """
        GRANT USAGE ON SCHEMA public TO app;
        GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO app;
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app;
        REVOKE INSERT, UPDATE ON audit_event, audit_checkpoint FROM app;
        GRANT INSERT ON audit_checkpoint TO app;
        ALTER DEFAULT PRIVILEGES FOR ROLE migrator IN SCHEMA public GRANT SELECT, INSERT, UPDATE ON TABLES TO app;
        ALTER DEFAULT PRIVILEGES FOR ROLE migrator IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO app;

        -- Row-level security for tenant tables
        ALTER TABLE instrument ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS instrument_scope ON instrument;
        CREATE POLICY instrument_scope ON instrument FOR ALL
          USING (
            current_setting('app.role', true) IN ('bureau','auditor')
            OR (current_setting('app.role', true) = 'regional' AND region = current_setting('app.region', true))
            OR (current_setting('app.role', true) = 'institution' AND institution_id::text = current_setting('app.institution', true))
          )
          WITH CHECK (
            current_setting('app.role', true) <> 'auditor' AND (
              current_setting('app.role', true) = 'bureau'
              OR (current_setting('app.role', true) = 'regional' AND region = current_setting('app.region', true))
              OR (current_setting('app.role', true) = 'institution' AND institution_id::text = current_setting('app.institution', true))
            )
          );

        ALTER TABLE institution ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS institution_scope ON institution;
        CREATE POLICY institution_scope ON institution FOR ALL
          USING (
            current_setting('app.role', true) IN ('bureau','auditor')
            OR (current_setting('app.role', true) = 'regional' AND region = current_setting('app.region', true))
            OR (current_setting('app.role', true) = 'institution' AND id::text = current_setting('app.institution', true))
          )
          WITH CHECK (current_setting('app.role', true) = 'bureau');

        DO $$
        DECLARE t text;
        BEGIN
          FOREACH t IN ARRAY ARRAY['document','confirmation','obligation','notice','case_note','flag_waiver','release_request'] LOOP
            EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
            EXECUTE format('DROP POLICY IF EXISTS %I ON %I', t || '_scope', t);
            EXECUTE format($p$CREATE POLICY %I ON %I FOR ALL
              USING (EXISTS (SELECT 1 FROM instrument i WHERE i.id = %I.instrument_id))
              WITH CHECK (current_setting('app.role', true) <> 'auditor'
                          AND EXISTS (SELECT 1 FROM instrument i WHERE i.id = %I.instrument_id))$p$,
              t || '_scope', t, t, t);
          END LOOP;
        END $$;

        ALTER TABLE audit_event ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS audit_read ON audit_event;
        CREATE POLICY audit_read ON audit_event FOR SELECT
          USING (current_setting('app.role', true) IN ('bureau','auditor'));
        """
    )

    # 13. Audit Cryptographic Functions & Triggers
    op.execute(
        """
        CREATE OR REPLACE FUNCTION audit_digest(p_prev text, p_ts timestamptz, p_actor uuid, p_action text,
                                     p_entity text, p_entity_id text, p_payload jsonb)
        RETURNS text LANGUAGE sql IMMUTABLE AS $$
          SELECT encode(sha256(convert_to(
            p_prev || '|' || to_char(p_ts AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"') || '|' ||
            COALESCE(p_actor::text, '') || '|' || p_action || '|' || p_entity || '|' || p_entity_id || '|' ||
            p_payload::text, 'UTF8')), 'hex')
        $$;

        CREATE OR REPLACE FUNCTION audit_append(p_actor uuid, p_action text, p_entity text, p_entity_id text, p_payload jsonb)
        RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
        DECLARE v_prev text; v_ts timestamptz := clock_timestamp(); v_id bigint; v_payload jsonb := COALESCE(p_payload, '{}');
        BEGIN
          PERFORM pg_advisory_xact_lock(hashtext('audit_chain'));
          SELECT hash INTO v_prev FROM audit_event ORDER BY id DESC LIMIT 1;
          v_prev := COALESCE(v_prev, repeat('0', 64));
          INSERT INTO audit_event(ts, actor_id, action, entity, entity_id, payload, prev_hash, hash)
          VALUES (v_ts, p_actor, p_action, p_entity, p_entity_id, v_payload, v_prev,
                  audit_digest(v_prev, v_ts, p_actor, p_action, p_entity, p_entity_id, v_payload))
          RETURNING id INTO v_id;
          RETURN v_id;
        END $$;

        CREATE OR REPLACE FUNCTION audit_verify() RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
        DECLARE r record; v_expected_prev text := repeat('0', 64);
        BEGIN
          FOR r IN SELECT * FROM audit_event ORDER BY id LOOP
            IF r.prev_hash <> v_expected_prev OR
               r.hash <> audit_digest(r.prev_hash, r.ts, r.actor_id, r.action, r.entity, r.entity_id, r.payload) THEN
              RETURN r.id;
            END IF;
            v_expected_prev := r.hash;
          END LOOP;
          RETURN NULL;
        END $$;

        CREATE OR REPLACE FUNCTION audit_no_change() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'audit_event is append-only'; END $$;

        DROP TRIGGER IF EXISTS audit_event_append_only ON audit_event;
        CREATE TRIGGER audit_event_append_only BEFORE UPDATE OR DELETE ON audit_event
          FOR EACH ROW EXECUTE FUNCTION audit_no_change();

        DROP TRIGGER IF EXISTS audit_event_no_truncate ON audit_event;
        CREATE TRIGGER audit_event_no_truncate BEFORE TRUNCATE ON audit_event
          FOR EACH STATEMENT EXECUTE FUNCTION audit_no_change();

        REVOKE ALL ON FUNCTION audit_append(uuid,text,text,text,jsonb) FROM PUBLIC;
        REVOKE ALL ON FUNCTION audit_verify() FROM PUBLIC;
        GRANT EXECUTE ON FUNCTION audit_append(uuid,text,text,text,jsonb) TO app;
        GRANT EXECUTE ON FUNCTION audit_verify() TO app;
        """
    )


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS audit_event_no_truncate ON audit_event;")
    op.execute("DROP TRIGGER IF EXISTS audit_event_append_only ON audit_event;")
    op.execute("DROP FUNCTION IF EXISTS audit_no_change();")
    op.execute("DROP FUNCTION IF EXISTS audit_verify();")
    op.execute("DROP FUNCTION IF EXISTS audit_append(uuid,text,text,text,jsonb);")
    op.execute("DROP FUNCTION IF EXISTS audit_digest(text,timestamptz,uuid,text,text,text,jsonb);")
    op.drop_constraint('fk_user_institution_id_institution', 'user', type_='foreignkey')
    op.drop_column('user', 'institution_id')
    op.drop_column('user', 'region')
    op.drop_column('user', 'role')
    op.drop_table('notice')
    op.drop_table('confirmation')
    op.drop_table('release_request')
    op.drop_table('obligation')
    op.drop_table('flag_waiver')
    op.drop_table('document')
    op.drop_table('case_note')
    op.drop_table('instrument')
    op.drop_table('institution')
    op.drop_table('audit_event')
    op.drop_table('audit_checkpoint')
