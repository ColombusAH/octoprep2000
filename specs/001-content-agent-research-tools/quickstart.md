# Quickstart: Content Agent Research Tools

**Feature**: `001-content-agent-research-tools`  
Validate end-to-end after implementation.

## Prerequisites

- Backend running: `make backend`
- Postgres up: `make db-up`
- `.env` configured:
  - `LITELLM_API_KEY` (required for classification + evaluation)
  - `EXA_API_KEY` (required for live article/improvement search tests)
  - `CONTEXT7_API_KEY` (optional; recommended for doc fetch tests)
  - `DEMO_MODE` unset or empty for live tests

## Scenario 1: Technical topic with grounded findings (happy path)

1. Create session:
   ```bash
   curl -s -X POST http://localhost:8000/sessions \
     -H 'Content-Type: application/json' \
     -d '{"topic":"React 19 new features","topic_context":"Focus on Server Components and Compiler"}' \
     | tee /tmp/session.json
   ```
2. Note `session_id` and `access_token` from response.
3. Upload a PPTX (optional) and run a short rehearsal with deliberate content, or inject transcript via test harness if available.
4. End session:
   ```bash
   curl -s -X POST "http://localhost:8000/sessions/{session_id}/end?access_token={token}"
   ```
5. Fetch report:
   ```bash
   curl -s "http://localhost:8000/sessions/{session_id}/report?access_token={token}" | jq .
   ```

**Expected**:
- `content_research_status` is `full` or `partial`
- `content_score` > 0
- At least one content insight with category `content`
- Improvement or coverage-gap insight references topic-specific substance (not generic filler)
- Report returns within 60 seconds

## Scenario 2: Demo replay unchanged

1. Set `DEMO_MODE=replay` in `.env`; restart backend.
2. Create session, end immediately (transcript may be empty or from replay audio).
3. Fetch report.

**Expected**:
- No external API calls (verify logs: no Exa/Context7 lines)
- `content_research_status` is `not_applicable` or fixture-appropriate
- Content findings match `packages/backend/fixtures/content_findings.json` shape

## Scenario 3: Research degradation

1. Set `EXA_API_KEY=` (empty) and invalid `CONTEXT7_API_KEY`; keep `LITELLM_API_KEY` valid.
2. Create technical session, add transcript, end session.

**Expected**:
- Report still returns 200
- `content_research_status` is `skipped` or `partial`
- Content insight mentions reference lookup unavailable
- `content_score` still computed (not null / not "Content analysis skipped")

## Scenario 4: Non-technical topic

1. Create session with topic `"My career journey in enterprise sales"`.
2. End session with any transcript.

**Expected**:
- `content_research_status` is `not_applicable`
- No Exa/Context7 calls in logs
- Transcript-only analysis runs

## Scenario 5: Frontend status visibility

1. Open `/session/{session_id}/report?access_token={token}` in browser.
2. Scroll to Technical Content panel.

**Expected**:
- Disclaimer mentions live reference lookup when `content_research_status` is `full`
- Text status visible when `partial` or `skipped` (not color-only)
- Brain / Technical Content panel shows strengths and improvements

## Automated tests

```bash
cd packages/backend && uv run pytest tests/test_content_research.py tests/test_report_dedup.py -q
```

**Expected**: all pass.

## Manual timing check

```bash
time curl -s -X POST "http://localhost:8000/sessions/{session_id}/end?access_token={token}"
```

**Expected**: real < 60s for typical 5-minute rehearsal transcript.
