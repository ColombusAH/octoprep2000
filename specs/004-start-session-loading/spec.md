# Feature Specification: Start Session Loading State

**Feature Branch**: `004-start-session-loading`

**Created**: 2026-06-24

**Status**: Draft

**Input**: User description: "start session button doesn't show loading state."

## Summary

When a presenter starts a rehearsal session, the Start Session button currently gives no clear feedback that work is in progress. This makes the flow feel unresponsive and can lead to repeated clicks while the session is being created or prepared. This feature makes the session-start action visibly enter a loading state, prevents duplicate starts during that pending period, and returns to an actionable state if session start fails.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See Session Start Progress (Priority: P1)

As a presenter ready to rehearse, I want the Start Session button to clearly show that the session is starting after I click it, so I know the app received my action and I should wait.

**Why this priority**: This is the reported issue and directly affects the core rehearsal entry point. Without visible progress, users can mistake a valid pending operation for a broken button.

**Independent Test**: Use a normal prepared session, click Start Session, and verify that the button immediately changes to a visible loading state until the session transition succeeds or fails.

**Acceptance Scenarios**:

1. **Given** the presenter can start a prepared session, **When** they click Start Session, **Then** the button immediately shows a loading indicator and loading text while start is pending.
2. **Given** session start is pending, **When** the presenter views the button, **Then** the button communicates progress using text or an icon in addition to any color change.
3. **Given** session start succeeds, **When** the app transitions into the rehearsal experience, **Then** the loading state does not remain visible on the previous control.

---

### User Story 2 - Prevent Duplicate Session Starts (Priority: P1)

As a presenter, I want the Start Session control to ignore repeated clicks while the first start is still pending, so I do not accidentally create duplicate sessions or trigger conflicting transitions.

**Why this priority**: A loading state that still allows duplicate submission only fixes perception, not the underlying user-risk. The action must be protected while pending.

**Independent Test**: Click Start Session multiple times rapidly and verify that only one start attempt is accepted while the loading state is active.

**Acceptance Scenarios**:

1. **Given** Start Session has been clicked once, **When** the presenter clicks the button again before the first attempt completes, **Then** the second click does not start another attempt.
2. **Given** session start is pending, **When** the presenter uses keyboard activation on the button, **Then** duplicate activation is also prevented.

---

### User Story 3 - Recover from Start Failure (Priority: P2)

As a presenter, I want the Start Session button to become usable again if starting fails, so I can retry without refreshing the page.

**Why this priority**: Failure recovery is necessary for a credible demo and avoids trapping the user in a permanent loading state.

**Independent Test**: Simulate a failed session-start attempt and verify the loading state clears, an error is visible, and the presenter can retry.

**Acceptance Scenarios**:

1. **Given** Start Session is pending, **When** the start attempt fails, **Then** the button exits the loading state and becomes actionable again.
2. **Given** a start failure occurred, **When** the presenter views the page, **Then** a clear user-facing failure message is shown near the start action or session status area.
3. **Given** the button has recovered after failure, **When** the presenter clicks Start Session again, **Then** a new single start attempt begins and the loading state is shown again.

### Edge Cases

- **Very fast success**: the loading state may be brief, but the button still changes state immediately after activation before transition completes.
- **Slow start path**: the loading state remains visible for the full pending duration and does not time out silently.
- **Network or service failure**: loading clears and a retry path is available; the presenter is not stuck.
- **Keyboard and assistive technology activation**: pending state and disabled/unavailable behavior apply consistently beyond mouse clicks.
- **Existing unavailable state**: if Start Session is already unavailable because prerequisites are missing, this feature does not make it clickable.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST visibly change the Start Session button to a loading state immediately after the presenter activates it and before the session-start attempt completes.
- **FR-002**: The loading state MUST include non-color feedback, such as progress text, an accessible busy indication, or a visible indicator accompanied by text.
- **FR-003**: The Start Session action MUST accept only one start attempt while a previous attempt is pending.
- **FR-004**: The pending state MUST block duplicate activation from mouse, touch, keyboard, or assistive technology interactions.
- **FR-005**: When session start succeeds, the system MUST transition to the rehearsal experience without leaving the start control in a stale loading state.
- **FR-006**: When session start fails, the system MUST clear the loading state, make the Start Session action available again if prerequisites still allow it, and show a clear retryable error message.
- **FR-007**: The loading behavior MUST preserve existing rules that keep Start Session unavailable until the session is ready to start.
- **FR-008**: The loading and failure states MUST be understandable on desktop and mobile layouts.

### Constitution-Aligned Requirements *(mandatory)*

- **CAR-001**: This feature affects the core demo path at the live rehearsal start point. It must preserve the existing flow from PPTX upload to live rehearsal capture, session end, and `/session/:id/report`.
- **CAR-002**: This feature does not change API contracts, WebSocket payloads, agent payloads, scoring, shared types, or database contracts; it only changes user-facing session-start state behavior.
- **CAR-003**: Session isolation behavior is unchanged. Starting a session continues to require the existing session ownership context and must not introduce new `access_token` or `share_token` handling.
- **CAR-004**: Failure and slow-start paths must degrade safely: the UI must not hang indefinitely without feedback, and retry must be possible after a failed start attempt.
- **CAR-005**: The loading state, disabled/unavailable state, and failure state must not rely on color alone; they must include text or other non-color status indicators.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In 100% of manual start-session attempts, the Start Session control shows a visible pending state immediately after activation and before completion.
- **SC-002**: During a pending start, rapid repeated activation results in exactly one accepted start attempt.
- **SC-003**: After a simulated start failure, the loading state clears within 1 second of the failure being known, a clear error is visible, and the user can retry without refreshing.
- **SC-004**: The pending, unavailable, and failure states are distinguishable without relying on color alone on both desktop and mobile.
- **SC-005**: The existing successful session-start flow still reaches the rehearsal experience and does not regress the later report path.

## Assumptions

- The affected control is the existing Start Session button in the prepared-session/rehearsal setup flow.
- The session-start operation may take long enough for visual feedback to matter, even if it is often fast locally.
- A failed start attempt should be retryable when the original session prerequisites remain satisfied.
- This feature is limited to the start-session UI state and duplicate-action prevention; it does not redesign the full rehearsal setup screen.
