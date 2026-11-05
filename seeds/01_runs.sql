-- Initialize Runs Ledger Table
CREATE TABLE IF NOT EXISTS runs (
    run_id VARCHAR(255) PRIMARY KEY,
    sandbox_name VARCHAR(255) NOT NULL UNIQUE,
    problem_id VARCHAR(255) NOT NULL,
    state VARCHAR(50) NOT NULL,
    execution_target VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Seed row
-- The seed row uses sandbox name sbx-seeddemo1, state deleted, execution target celesto_sandbox,
-- and re-running the SQL does not duplicate it.
INSERT INTO runs (run_id, sandbox_name, problem_id, state, execution_target)
VALUES ('run-seed001', 'sbx-seeddemo1', 'web-qa-detonation-seed', 'deleted', 'celesto_sandbox')
ON CONFLICT (run_id) DO NOTHING;
