-- Query indexes for list, dashboard, action queue and child-record lookups.
-- This file is documentation and an operations fallback; Alembic is authoritative.
CREATE INDEX IF NOT EXISTS instrument_maturity_idx
    ON instrument (maturity_date, lifecycle);
CREATE INDEX IF NOT EXISTS instrument_active_region_idx
    ON instrument (region, maturity_date)
    WHERE lifecycle IN ('pending', 'active', 'matured', 'renewed');
CREATE INDEX IF NOT EXISTS confirmation_status_idx
    ON confirmation (instrument_id, status, confirmed_at);
CREATE INDEX IF NOT EXISTS obligation_open_due_idx
    ON obligation (due_date, owner_role)
    WHERE status = 'open';
CREATE INDEX IF NOT EXISTS notice_instrument_sent_idx
    ON notice (instrument_id, sent_at);
CREATE INDEX IF NOT EXISTS case_note_instrument_created_idx
    ON case_note (instrument_id, created_at);
CREATE INDEX IF NOT EXISTS flag_waiver_instrument_code_idx
    ON flag_waiver (instrument_id, code);
CREATE INDEX IF NOT EXISTS release_request_status_idx
    ON release_request (status, updated_at);
