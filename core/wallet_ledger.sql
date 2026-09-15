-- ==============================================================================
-- LUQI-AI WALLET LEDGER & IDEMPOTENCY SCHEMA (append to migration files)
-- Execute on the production cluster AFTER core/security_rls.sql.
-- NOTE: gen_random_uuid() is native in PostgreSQL 13+ (pgcrypto before that).
-- ==============================================================================

-- 1. Secure ledger tables tracking all currency movements
CREATE TABLE IF NOT EXISTS wallet_ledgers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    balance NUMERIC(15, 4) NOT NULL DEFAULT 0.0000,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS wallet_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    amount NUMERIC(15, 4) NOT NULL,              -- positive = deposit, negative = lab usage debit
    transaction_type VARCHAR(50) NOT NULL,       -- 'deposit' | 'lab_usage_debit' | 'subsidy_allocation'
    reference_id VARCHAR(150) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 2. Idempotency: duplicate reference settlement is rejected at the database level
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_payment_reference ON wallet_transactions (reference_id);

-- 3. FORCE Row-Level Security (owner bypass closed, same as core/security_rls.sql)
ALTER TABLE wallet_ledgers ENABLE ROW LEVEL SECURITY;
ALTER TABLE wallet_ledgers FORCE ROW LEVEL SECURITY;
ALTER TABLE wallet_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE wallet_transactions FORCE ROW LEVEL SECURITY;

CREATE POLICY ledger_geo_isolation_policy ON wallet_ledgers
    FOR ALL TO luqi_app_user
    USING (student_id IN (SELECT id FROM students
        WHERE country_code = NULLIF(current_setting('app.current_user_country', true), '')));

CREATE POLICY tx_geo_isolation_policy ON wallet_transactions
    FOR ALL TO luqi_app_user
    USING (student_id IN (SELECT id FROM students
        WHERE country_code = NULLIF(current_setting('app.current_user_country', true), '')));
