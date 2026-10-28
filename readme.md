# Autonomous Multi-Agent GitHub PR Review System

A production-grade, event-driven multi-agent CI/CD code review engine powered by FastAPI, Groq (Qwen 27B), Neon PostgreSQL, and GitHub REST API.

---

## Architecture Overview

When a developer opens or updates a Pull Request on GitHub, this system automatically intercepts the webhook event, downloads the modified diff, orchestrates specialized AI agents to evaluate the code, and posts structured, actionable feedback directly to the PR within seconds.

```text
               [Developer Opens / Syncs Pull Request]
                                 │
                                 ▼
           [GitHub Webhook: POST /webhook (HMAC Signed)]
                                 │
                                 ▼
                  [FastAPI Verification Gateway]
             ├── Constant-time HMAC-SHA256 signature check
             ├── Event filtering (opened, synchronize, reopened)
             └── Immediate 200 OK (<10ms) via BackgroundTasks
                                 │
                                 ▼
                    [GitHub REST API Client]
             └── Asynchronous fetch of PR context & file diffs
                                 │
                                 ▼
                     [Multi-Agent Orchestrator]
                                 │
       ┌─────────────────────────┼─────────────────────────┐
       ▼                         ▼                         ▼
[Security Agent]         [Quality Agent]         [Performance Agent]
(SQLi, Keys, Deser.)     (Errors, Clean Code)    (Loops, N+1 Queries)
       │                         │                         │
       └─────────────────────────┼─────────────────────────┘
                                 │
                                 ▼
                   [Deterministic Python Validator]
             ├── Cross-agent deduplication
             ├── Confidence thresholding (<0.65 pruned)
             └── Max 5 findings / file cap
                                 │
                                 ▼
                      [Summary Review Agent]
             └── Compiles findings into clean GitHub Markdown
                                 │
                                 ▼
                    [GitHub REST API Commenter]
             └── Posts review comment directly to the PR
                                 │
                                 ▼
                  [Neon PostgreSQL Audit Trail]
             └── Records latency, token metrics, and findings
```

---

## Key Features

- **Asynchronous and Non-Blocking**: Uses FastAPI and `asyncio.gather` so agents run concurrently. Webhook endpoints return `200 OK` in milliseconds to satisfy GitHub's 10-second timeout.
- **Cryptographic Security**: Constant-time verification of `X-Hub-Signature-256` using HMAC-SHA256 to prevent spoofing and timing attacks.
- **Specialized Multi-Agent Committee**:
  - **Security Agent**: Spots hardcoded keys, SQL injection, insecure deserialization, and missing authentication.
  - **Quality Agent**: Detects unhandled exceptions, swallowed errors, and dead code.
  - **Performance Agent**: Detects N+1 query patterns, unpaginated collections, and inefficient nested loops.
- **Zero-Hallucination Guarantees**:
  - Enforced JSON schemas via Pydantic v2.
  - Strict evidence-based system prompts that produce empty findings lists on clean code.
- **Enterprise Relational Observability**: Normalized PostgreSQL schema with complete audit logging for repositories, pull requests, review runs, individual findings, and raw webhook deliveries.

---

## Database Architecture (Neon PostgreSQL)

The backend uses a normalized, relational PostgreSQL schema with UUID primary keys, foreign key constraints, and JSONB audit trails:

| Table | Description |
|---|---|
| `repositories` | Tracked GitHub repositories (`github_repo_id`, `full_name`, `owner`, `name`). |
| `pull_requests` | Pull request metadata linked to repositories. |
| `review_runs` | Individual review lifecycle executions (`status`, `latency_ms`, `total_files_changed`). |
| `changed_files` | Granular diff patches, status (`added`, `modified`), and inferred languages. |
| `agent_runs` | Per-agent telemetry (tokens, latency, status, input/output JSONB). |
| `findings` | Atomic issues (`severity`, `issue`, `recommendation`, `confidence`, `reviewer_decision`). |
| `github_comments` | Audit log of posted review comments with delivery URLs. |
| `webhook_events` | Append-only raw audit log of all incoming GitHub webhook payloads. |

---

## Tech Stack

- **Backend Framework**: Python 3.12, FastAPI, Uvicorn (ASGI)
- **AI / LLM Inference**: Groq Cloud API (`qwen/qwen3.8-27b`)
- **Database**: Neon Serverless PostgreSQL, SQLAlchemy (Async), `asyncpg`
- **Data Validation**: Pydantic v2, Pydantic Settings
- **HTTP Client**: `httpx` (Asynchronous HTTP with redirect support)
- **Version Control and CI**: Git, GitHub REST API, GitHub Webhooks

---

## Getting Started

### 1. Clone and Set Up Environment

```bash
git clone https://github.com/Abhijith099/autonomous-pr-reviewer.git
cd autonomous-pr-reviewer

python -m venv venv
# On Windows:
.\venv\Scripts\Activate.ps1
# On macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the root directory:

```env
DATABASE_URL=postgresql+asyncpg://<username>:<password>@<neon-host>/<dbname>
GITHUB_TOKEN=ghp_your_personal_access_token_here
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here
GROQ_API_KEY=gsk_your_groq_api_key_here
ENVIRONMENT=development
```

### 3. Initialize Database Schema

Execute the initialization script to provision all 8 tables and indexes on Neon:

```bash
python init_db.py
```

### 4. Start the Application

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://127.0.0.1:8000`.

---

## Verification and Testing

### 1. Health Check
```bash
curl http://127.0.0.1:8000/health
```

### 2. Standalone Security Agent Verification
Tests the security agent against simulated vulnerabilities (SQL injection, leaked keys) and validates zero false positives on clean diffs:
```bash
python test_security_agent.py
```

### 3. End-to-End Webhook Simulation
Simulates an HMAC-SHA256 signed GitHub webhook delivery against a live PR, triggers background review, and persists results to Neon:
```bash
python test_webhook.py
```

### 4. Inspect Database Audit Log
```bash
python check_db.py
```