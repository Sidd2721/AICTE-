-- For MANAGED Postgres (Neon etc.) where you cannot create a second login-capable owner or a superuser.
-- Run ONCE, connected as the provider's default OWNER role (e.g. neondb_owner), using plain SQL:
--   psql "<OWNER direct connection string>" -v ON_ERROR_STOP=1 -v owner=neondb_owner -v dbname=neondb -v app_pw="'<strong password>'" -f scripts/db-roles-managed.sql
-- WHY plain SQL: on Neon, roles created in the console/CLI/API join neon_superuser and get BYPASSRLS.
-- A role created with CREATE ROLE here does not, so row-level security really applies to it.
CREATE ROLE app LOGIN PASSWORD :app_pw NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
GRANT CONNECT ON DATABASE :"dbname" TO app;
GRANT USAGE ON SCHEMA public TO app;
-- Tables/sequences the OWNER creates later (via Alembic) are usable by app: DML only, no TRUNCATE, no DDL.
ALTER DEFAULT PRIVILEGES FOR ROLE :"owner" IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app;
ALTER DEFAULT PRIVILEGES FOR ROLE :"owner" IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO app;
-- Prove it: both must be false for app.
SELECT rolname, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = 'app';
