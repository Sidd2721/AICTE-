-- verify: hardening
GRANT USAGE ON SCHEMA public TO app;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app;
REVOKE INSERT, UPDATE ON audit_event, audit_checkpoint FROM app;
GRANT INSERT ON audit_checkpoint TO app;
ALTER DEFAULT PRIVILEGES FOR ROLE migrator IN SCHEMA public GRANT SELECT, INSERT, UPDATE ON TABLES TO app;
ALTER DEFAULT PRIVILEGES FOR ROLE migrator IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO app;

-- Row-level security. Context comes from set_config(): app.role, app.region, app.institution.
ALTER TABLE instrument ENABLE ROW LEVEL SECURITY;
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
    EXECUTE format($p$CREATE POLICY %I ON %I FOR ALL
      USING (EXISTS (SELECT 1 FROM instrument i WHERE i.id = %I.instrument_id))
      WITH CHECK (current_setting('app.role', true) <> 'auditor'
                  AND EXISTS (SELECT 1 FROM instrument i WHERE i.id = %I.instrument_id))$p$,
      t || '_scope', t, t, t);
  END LOOP;
END $$;

-- audit rows are readable only by bureau and auditor; all writes go through audit_append()
ALTER TABLE audit_event ENABLE ROW LEVEL SECURITY;
CREATE POLICY audit_read ON audit_event FOR SELECT
  USING (current_setting('app.role', true) IN ('bureau','auditor'));
