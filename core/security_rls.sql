-- ==============================================================================
-- LUQI-AI GEOGRAPHIC DATA SOVEREIGNTY POLICIES (POPIA / Kenya DPA)
-- Execute ONCE on the production cluster as a migration (see deploy/DEPLOYMENT.md).
-- Requires: app role 'luqi_app_user' (the role the FastAPI pool connects as,
-- NOT the table owner - FORCE RLS closes the owner-bypass hole).
-- ==============================================================================

-- 0. Ensure the application role exists (adjust password via vault)
-- CREATE ROLE luqi_app_user LOGIN PASSWORD '...';

-- 1. Enable + FORCE Row-Level Security on core operational tables.
--    FORCE means even the table owner is subject to policies.
ALTER TABLE students ENABLE ROW LEVEL SECURITY;
ALTER TABLE students FORCE ROW LEVEL SECURITY;
ALTER TABLE lab_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE lab_progress FORCE ROW LEVEL SECURITY;
ALTER TABLE payment_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment_transactions FORCE ROW LEVEL SECURITY;
ALTER TABLE sovereign_enterprises ENABLE ROW LEVEL SECURITY;
ALTER TABLE sovereign_enterprises FORCE ROW LEVEL SECURITY;

-- 2. Drop legacy isolation templates to avoid dependency conflicts on re-runs
DROP POLICY IF EXISTS student_geo_isolation_policy ON students;
DROP POLICY IF EXISTS progress_geo_isolation_policy ON lab_progress;
DROP POLICY IF EXISTS payment_geo_isolation_policy ON payment_transactions;
DROP POLICY IF EXISTS enterprise_geo_isolation_policy ON sovereign_enterprises;

-- 3. Policy maps bound to the per-request session context set by core/rls.py.
--    NULLIF(..., '') -> NULL when unset, and country_code = NULL matches nothing:
--    an unauthenticated session sees ZERO rows. Fail-closed by construction.
CREATE POLICY student_geo_isolation_policy ON students
    FOR ALL TO luqi_app_user
    USING (country_code = NULLIF(current_setting('app.current_user_country', true), ''));

CREATE POLICY progress_geo_isolation_policy ON lab_progress
    FOR ALL TO luqi_app_user
    USING (student_id IN (
        SELECT id FROM students
        WHERE country_code = NULLIF(current_setting('app.current_user_country', true), '')
    ));

CREATE POLICY payment_geo_isolation_policy ON payment_transactions
    FOR ALL TO luqi_app_user
    USING (student_id IN (
        SELECT id FROM students
        WHERE country_code = NULLIF(current_setting('app.current_user_country', true), '')
    ));

CREATE POLICY enterprise_geo_isolation_policy ON sovereign_enterprises
    FOR ALL TO luqi_app_user
    USING (country_code = NULLIF(current_setting('app.current_user_country', true), ''));
