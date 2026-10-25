-- verify: schema
CREATE TABLE institution (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  permanent_id text NOT NULL UNIQUE,
  name text NOT NULL,
  region text NOT NULL,
  is_government boolean NOT NULL DEFAULT false,
  leased_private boolean NOT NULL DEFAULT false,
  programmes jsonb NOT NULL DEFAULT '[]'
);
-- template table, shown only so foreign keys resolve; extend it via an Alembic migration
CREATE TABLE "user" (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email text NOT NULL UNIQUE,
  role text NOT NULL CHECK (role IN ('institution','regional','bureau','auditor')),
  region text,
  institution_id uuid REFERENCES institution(id)
);
CREATE TABLE instrument (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  institution_id uuid NOT NULL REFERENCES institution(id),
  region text NOT NULL,
  kind text NOT NULL CHECK (kind IN ('FDR','RTGS')),
  ref_no text NOT NULL,
  bank_code text NOT NULL,
  ifsc text NOT NULL,
  amount_paise bigint NOT NULL CHECK (amount_paise > 0),
  issue_date date NOT NULL,
  maturity_date date NOT NULL,
  holders jsonb NOT NULL DEFAULT '[]',
  lien_marked boolean NOT NULL DEFAULT false,
  is_duplicate_receipt boolean NOT NULL DEFAULT false,
  lifecycle text NOT NULL DEFAULT 'pending'
    CHECK (lifecycle IN ('pending','active','matured','renewed','released')),
  replaces_id uuid REFERENCES instrument(id),
  created_by uuid REFERENCES "user"(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX instrument_region_idx ON instrument(region);
CREATE INDEX instrument_institution_idx ON instrument(institution_id);
CREATE INDEX instrument_ref_idx ON instrument(bank_code, ref_no);
CREATE TABLE document (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  instrument_id uuid NOT NULL REFERENCES instrument(id),
  kind text NOT NULL CHECK (kind IN ('fdr_scan','payment_proof','bank_letter','affidavit','certificate','indemnity','other')),
  version int NOT NULL CHECK (version >= 1),
  filename text NOT NULL,
  mime text NOT NULL,
  size_bytes bigint NOT NULL CHECK (size_bytes > 0),
  sha256 text NOT NULL,
  storage_key text NOT NULL,
  uploaded_by uuid REFERENCES "user"(id),
  uploaded_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (instrument_id, kind, version)
);
CREATE TABLE confirmation (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  instrument_id uuid NOT NULL REFERENCES instrument(id),
  status text NOT NULL DEFAULT 'requested'
    CHECK (status IN ('requested','confirmed','rejected','unavailable')),
  method text NOT NULL CHECK (method IN ('signed_letter','callback','manual')),
  token_hash text NOT NULL,
  token_expires_at timestamptz NOT NULL,
  token_used_at timestamptz,
  fields jsonb,
  evidence_document_id uuid REFERENCES document(id),
  requested_at timestamptz NOT NULL DEFAULT now(),
  confirmed_at timestamptz,
  expires_at timestamptz,
  revoked boolean NOT NULL DEFAULT false,
  CHECK (status <> 'confirmed' OR (fields IS NOT NULL AND confirmed_at IS NOT NULL AND expires_at IS NOT NULL))
);
CREATE TABLE obligation (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  instrument_id uuid NOT NULL REFERENCES instrument(id),
  kind text NOT NULL CHECK (kind IN ('confirmation_due','maturity','renewal_due','release_clearance')),
  due_date date NOT NULL,
  status text NOT NULL DEFAULT 'open' CHECK (status IN ('open','done','waived')),
  owner_role text NOT NULL CHECK (owner_role IN ('institution','regional','bureau')),
  UNIQUE (instrument_id, kind, due_date)
);
CREATE TABLE notice (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  instrument_id uuid NOT NULL REFERENCES instrument(id),
  obligation_id uuid NOT NULL REFERENCES obligation(id),
  step text NOT NULL,
  channel text NOT NULL DEFAULT 'email',
  sent_at timestamptz NOT NULL DEFAULT now(),
  delivered boolean NOT NULL DEFAULT false,
  UNIQUE (obligation_id, step)
);
CREATE TABLE case_note (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  instrument_id uuid NOT NULL REFERENCES instrument(id),
  author_id uuid NOT NULL REFERENCES "user"(id),
  body text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE flag_waiver (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  instrument_id uuid NOT NULL REFERENCES instrument(id),
  code text NOT NULL,
  reason text NOT NULL CHECK (length(reason) >= 10),
  waived_by uuid NOT NULL REFERENCES "user"(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (instrument_id, code)
);
CREATE TABLE release_request (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  instrument_id uuid NOT NULL REFERENCES instrument(id),
  path text NOT NULL CHECK (path IN ('term_completion','closure','merger','conversion')),
  checklist jsonb NOT NULL DEFAULT '[]',
  status text NOT NULL DEFAULT 'draft'
    CHECK (status IN ('draft','submitted','verified','approved','rejected','released')),
  requested_by uuid NOT NULL REFERENCES "user"(id),
  verified_by uuid REFERENCES "user"(id),
  approved_by uuid REFERENCES "user"(id),
  receipt_token text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (verified_by IS NULL OR approved_by IS NULL OR verified_by <> approved_by)
);
CREATE TABLE audit_event (
  id bigserial PRIMARY KEY,
  ts timestamptz NOT NULL,
  actor_id uuid,
  action text NOT NULL,
  entity text NOT NULL,
  entity_id text NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}',
  prev_hash text NOT NULL,
  hash text NOT NULL UNIQUE
);
CREATE TABLE audit_checkpoint (
  id bigserial PRIMARY KEY,
  up_to_id bigint NOT NULL,
  head_hash text NOT NULL,
  signature text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
