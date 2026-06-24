# Contract: Completion Signal

**Feature**: 001-agent-direct-persistence

The "notify that they finished processing" contract. In-process async method call — no broker
(Constitution Principle V).

## Interface

```python
CompletionKind = Literal["VIDEO", "AUDIO", "PPTX", "CONTENT", "REPORT"]

class CompletionSignal(BaseModel):
    session_id: uuid.UUID
    kind: CompletionKind
    meta: dict | None = None

# Orchestrator
async def notify_complete(self, session_id: uuid.UUID, kind: CompletionKind,
                          meta: dict | None = None) -> None: ...
def completed(self, session_id: uuid.UUID) -> set[CompletionKind]: ...
```

## Semantics

- An agent calls `orchestrator.notify_complete(...)` **only after** its corresponding DB write has
  committed. Ordering: `write → commit → notify`. Never notify before durability.
- The Orchestrator records the kind in `_completion[session_id]` and logs it.
- The signal is advisory coordination, not a data carrier — the data is already in the agreed
  tables. The Orchestrator reads the tables, not the signal payload.

## Consumption points

| Consumer | Uses signal to |
|---|---|
| `GET /sessions/:id` (`pptx_ready`) | Already reflects PPTXAgent's own `mark_pptx_ready` write; `PPTX` signal is the internal confirmation |
| `POST /sessions/:id/end` | Before ReportAgent reads `video_events`, ensure VisionAgent final flush done (await flush, then read) |
| Tests / observability | Assert each agent emitted its expected signal |

## Failure / edge handling (maps to spec Edge Cases + CAR-004)

- **Agent crashes after partial write, before signal**: Orchestrator MUST NOT treat the session as
  fully processed. Report path degrades safely — missing data falls through existing "No X captured"
  neutral defaults in ReportAgent scoring; audio-only fallback still applies for vision loss.
- **Signal lost / arrives before durability**: Orchestrator reads only committed rows; report
  assembly is triggered by `POST /:id/end`, which awaits the final flush with a bounded wait, then
  reads. No unbounded blocking on a missing signal.
- **Concurrent signals (different kinds)**: independent; `_completion` is a set, idempotent per kind.
- **`DEMO_MODE=replay`**: replay paths persist via the same agent helpers and emit the same signals;
  flow is identical.

## Non-goals

- No persistence of signals. No retry queue. No cross-process delivery. If a future multi-process
  deployment appears, this contract is the seam to replace — but that is out of scope (Principle V).
