-- Database roles for FDR Portal (AICTE PS 26265)
-- Database: app

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'migrator') THEN
        CREATE ROLE migrator LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD 'change-me-migrator';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app') THEN
        CREATE ROLE app LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD 'change-me-app';
    END IF;
END $$;

GRANT CONNECT ON DATABASE app TO migrator;
GRANT CONNECT ON DATABASE app TO app;
