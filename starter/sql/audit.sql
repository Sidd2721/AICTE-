-- verify: audit
CREATE FUNCTION audit_digest(p_prev text, p_ts timestamptz, p_actor uuid, p_action text,
                             p_entity text, p_entity_id text, p_payload jsonb)
RETURNS text LANGUAGE sql IMMUTABLE AS $$
  SELECT encode(sha256(convert_to(
    p_prev || '|' || to_char(p_ts AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"') || '|' ||
    COALESCE(p_actor::text, '') || '|' || p_action || '|' || p_entity || '|' || p_entity_id || '|' ||
    p_payload::text, 'UTF8')), 'hex')
$$;

CREATE FUNCTION audit_append(p_actor uuid, p_action text, p_entity text, p_entity_id text, p_payload jsonb)
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

CREATE FUNCTION audit_verify() RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
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

CREATE FUNCTION audit_no_change() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'audit_event is append-only'; END $$;
CREATE TRIGGER audit_event_append_only BEFORE UPDATE OR DELETE ON audit_event
  FOR EACH ROW EXECUTE FUNCTION audit_no_change();
CREATE TRIGGER audit_event_no_truncate BEFORE TRUNCATE ON audit_event
  FOR EACH STATEMENT EXECUTE FUNCTION audit_no_change();
REVOKE ALL ON FUNCTION audit_append(uuid,text,text,text,jsonb) FROM PUBLIC;
REVOKE ALL ON FUNCTION audit_verify() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION audit_append(uuid,text,text,text,jsonb) TO app;
GRANT EXECUTE ON FUNCTION audit_verify() TO app;
