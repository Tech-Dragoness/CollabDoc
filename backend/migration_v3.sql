-- ============================================================
-- Migration v3: simplify the access log to opens only
--
-- Run this ONLY if your database already has the document_access_log
-- table from a previous deploy (i.e. you already ran migration_v2.sql,
-- or an earlier setup.sql that included closed_at). Fresh installs should
-- just use the current setup.sql, which no longer creates this column.
--
--   psql "<DATABASE_URL>" -f migration_v3.sql
-- ============================================================

ALTER TABLE document_access_log DROP COLUMN IF EXISTS closed_at;