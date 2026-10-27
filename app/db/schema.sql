CREATE EXTENSION IF NOT EXISTS "pgcrypto";
-- 1. Repositories being monitored
CREATE TABLE IF NOT EXISTS repositories (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    github_repo_id  BIGINT UNIQUE NOT NULL,
    full_name       TEXT UNIQUE NOT NULL,
    owner           TEXT NOT NULL,
    name            TEXT NOT NULL,
    default_branch  TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- 2. Pull requests received from GitHub
CREATE TABLE IF NOT EXISTS pull_requests (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id       UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    github_pr_id        BIGINT UNIQUE NOT NULL,
    pr_number           INTEGER NOT NULL,
    title               TEXT,
    body                TEXT,
    author_login        TEXT,
    base_branch         TEXT,
    head_branch         TEXT,
    head_sha            TEXT,
    state               TEXT NOT NULL,
    is_draft            BOOLEAN NOT NULL DEFAULT FALSE,
    github_url          TEXT,
    opened_at           TIMESTAMPTZ,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (repository_id, pr_number)
);


-- 3. Raw webhook audit trail (Must be created before review_runs references it)
CREATE TABLE IF NOT EXISTS webhook_events (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    delivery_id         TEXT UNIQUE NOT NULL,
    event_type          TEXT NOT NULL,
    action              TEXT,
    repository_full_name TEXT,
    pr_number           INTEGER,
    signature_valid     BOOLEAN NOT NULL,
    processed           BOOLEAN NOT NULL DEFAULT FALSE,
    skip_reason         TEXT,
    payload             JSONB NOT NULL,
    received_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. One review execution per relevant webhook event
CREATE TABLE IF NOT EXISTS review_runs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pull_request_id     UUID NOT NULL REFERENCES pull_requests(id) ON DELETE CASCADE,
    webhook_event_id    UUID UNIQUE REFERENCES webhook_events(id),
    trigger_action      TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'queued',
    started_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMPTZ,
    total_files_changed INTEGER,
    total_additions     INTEGER,
    total_deletions     INTEGER,
    prompt_tokens       INTEGER DEFAULT 0,
    completion_tokens   INTEGER DEFAULT 0,
    total_tokens        INTEGER DEFAULT 0,
    estimated_cost_usd  NUMERIC(10, 6) DEFAULT 0,
    latency_ms          INTEGER,
    error_message       TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. Files included in the reviewed diff
CREATE TABLE IF NOT EXISTS changed_files (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_run_id       UUID NOT NULL REFERENCES review_runs(id) ON DELETE CASCADE,
    filename            TEXT NOT NULL,
    file_status         TEXT NOT NULL,
    language            TEXT,
    additions           INTEGER DEFAULT 0,
    deletions           INTEGER DEFAULT 0,
    patch               TEXT,
    raw_file_metadata   JSONB NOT NULL DEFAULT '{}'::JSONB,
    was_reviewed        BOOLEAN NOT NULL DEFAULT TRUE,
    skip_reason         TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. Each agent execution
CREATE TABLE IF NOT EXISTS agent_runs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_run_id       UUID NOT NULL REFERENCES review_runs(id) ON DELETE CASCADE,
    agent_name          TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'queued',
    model_name          TEXT,
    input_tokens        INTEGER DEFAULT 0,
    output_tokens       INTEGER DEFAULT 0,
    total_tokens        INTEGER DEFAULT 0,
    estimated_cost_usd  NUMERIC(10, 6) DEFAULT 0,
    latency_ms          INTEGER,
    input_payload       JSONB NOT NULL DEFAULT '{}'::JSONB,
    output_payload      JSONB NOT NULL DEFAULT '{}'::JSONB,
    error_message       TEXT,
    started_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMPTZ
);

-- 7. Individual issues identified by agents
CREATE TABLE IF NOT EXISTS findings (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_run_id       UUID NOT NULL REFERENCES review_runs(id) ON DELETE CASCADE,
    agent_run_id        UUID NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
    changed_file_id     UUID REFERENCES changed_files(id) ON DELETE SET NULL,
    agent_name          TEXT NOT NULL,
    severity            TEXT NOT NULL,
    category            TEXT,
    file_path           TEXT,
    line_hint           TEXT,
    issue               TEXT NOT NULL,
    recommendation      TEXT NOT NULL,
    confidence          NUMERIC(3, 2) CHECK (confidence BETWEEN 0 AND 1),
    is_duplicate        BOOLEAN NOT NULL DEFAULT FALSE,
    duplicate_of        UUID REFERENCES findings(id) ON DELETE SET NULL,
    included_in_comment BOOLEAN NOT NULL DEFAULT FALSE,
    reviewer_decision   TEXT,
    reviewer_note       TEXT,
    reviewed_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- 8. Comments posted back to GitHub
CREATE TABLE IF NOT EXISTS github_comments (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_run_id           UUID NOT NULL REFERENCES review_runs(id) ON DELETE CASCADE,
    github_comment_id       BIGINT UNIQUE,
    github_comment_url      TEXT,
    comment_body            TEXT NOT NULL,
    posted_at               TIMESTAMPTZ,
    post_status             TEXT NOT NULL DEFAULT 'pending',
    error_message           TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- Indexes for lightning fast queries
CREATE INDEX IF NOT EXISTS idx_pull_requests_repo ON pull_requests(repository_id);
CREATE INDEX IF NOT EXISTS idx_review_runs_pr ON review_runs(pull_request_id);
CREATE INDEX IF NOT EXISTS idx_review_runs_status ON review_runs(status);
CREATE INDEX IF NOT EXISTS idx_review_runs_created_at ON review_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_changed_files_run ON changed_files(review_run_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_review ON agent_runs(review_run_id);
CREATE INDEX IF NOT EXISTS idx_findings_review ON findings(review_run_id);
CREATE INDEX IF NOT EXISTS idx_findings_agent ON findings(agent_name);
CREATE INDEX IF NOT EXISTS idx_findings_severity ON findings(severity);
CREATE INDEX IF NOT EXISTS idx_findings_reviewer_decision ON findings(reviewer_decision);
CREATE INDEX IF NOT EXISTS idx_webhook_events_received_at ON webhook_events(received_at DESC);