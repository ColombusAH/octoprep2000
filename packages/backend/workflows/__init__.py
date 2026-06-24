"""agno Workflow layer for OctoPrep2000.

Two user-facing flows expressed as agno Workflows:
  - PptxPrepWorkflow  — pre-session, one-shot deck analysis (workflows/pptx_prep.py)
  - LiveSessionWorkflow — per-window live capture + analysis (workflows/live_session.py),
    driven by the LiveWindowAggregator (workflows/live_window.py); the report phase at
    session end is ReportWorkflow (workflows/report.py).

These Workflows are in-process orchestration glue only: telemetry=False, db=None. They
perform NO database writes and hold NO durable session state — the agents remain the sole
writers of their role-scoped tables (Constitution v2.0.0, Principle II) and the system stays
broker-free / in-process (Principle V).
"""

from __future__ import annotations
