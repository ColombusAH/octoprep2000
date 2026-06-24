/**
 * Capability-token client per TECH-ARCH §5.
 * access_token lives in localStorage keyed by session_id.
 * Never placed in URLs (except WS query param — accepted trade-off).
 */

export const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";
export const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

const TOKEN_KEY = (sessionId: string) => `octoprep:token:${sessionId}`;

export function storeToken(sessionId: string, token: string): void {
  try {
    localStorage.setItem(TOKEN_KEY(sessionId), token);
  } catch {
    /* SSR or quota — ignore */
  }
}

export function loadToken(sessionId: string): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY(sessionId));
  } catch {
    return null;
  }
}

function authHeaders(sessionId: string): HeadersInit {
  const token = loadToken(sessionId);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export type CreateSessionBody = { topic: string; topic_context?: string };

export async function createSession(
  body: CreateSessionBody,
): Promise<{ session_id: string; access_token: string }> {
  const res = await fetch(`${BACKEND_URL}/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`POST /sessions failed: ${res.status}`);
  return res.json();
}

export async function getSession(sessionId: string) {
  const res = await fetch(`${BACKEND_URL}/sessions/${sessionId}`, {
    headers: { ...authHeaders(sessionId) },
  });
  if (!res.ok) throw new Error(`GET /sessions/${sessionId} failed: ${res.status}`);
  return res.json();
}

export async function uploadPptx(sessionId: string, file: File): Promise<void> {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch(`${BACKEND_URL}/sessions/${sessionId}/upload`, {
    method: "POST",
    headers: { ...authHeaders(sessionId) },
    body: fd,
  });
  if (!res.ok) throw new Error(`upload failed: ${res.status}`);
}

/** Poll until PPTX prep finishes (deck analysis + pre-session topic research). */
export async function waitForPptxReady(
  sessionId: string,
  opts?: { timeoutMs?: number; intervalMs?: number },
): Promise<void> {
  const timeoutMs = opts?.timeoutMs ?? 60_000;
  const intervalMs = opts?.intervalMs ?? 1_000;
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const session = await getSession(sessionId);
    if (session.pptx_ready) return;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  throw new Error("Deck analysis timed out — try again or continue without slide feedback.");
}

/** Upload a pre-recorded rehearsal video for batch analysis (feature 003). */
export async function uploadVideo(sessionId: string, file: File): Promise<void> {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch(`${BACKEND_URL}/sessions/${sessionId}/upload-video`, {
    method: "POST",
    headers: { ...authHeaders(sessionId) },
    body: fd,
  });
  if (!res.ok) {
    let detail = `${res.status}`;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(`video upload failed: ${detail}`);
  }
}

/**
 * Poll session status until batch video analysis reaches a terminal state.
 * Resolves on REPORT_READY; throws with the failure reason on FAILED or timeout.
 */
export async function waitForVideoReady(
  sessionId: string,
  opts?: { timeoutMs?: number; intervalMs?: number },
): Promise<void> {
  const timeoutMs = opts?.timeoutMs ?? 20 * 60_000; // up to a 15-min video + processing
  const intervalMs = opts?.intervalMs ?? 3_000;
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const session = await getSession(sessionId);
    if (session.status === "REPORT_READY") return;
    if (session.status === "FAILED") {
      throw new Error(session.status_detail || "Video analysis failed.");
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  throw new Error("Video analysis timed out — try again or use a shorter video.");
}

export async function endSession(sessionId: string): Promise<void> {
  const res = await fetch(`${BACKEND_URL}/sessions/${sessionId}/end`, {
    method: "POST",
    headers: { ...authHeaders(sessionId) },
  });
  if (!res.ok) throw new Error(`end failed: ${res.status}`);
}

export async function getReport(sessionId: string, share?: string) {
  const qs = share ? `?share=${encodeURIComponent(share)}` : "";
  const headers: HeadersInit = share ? {} : authHeaders(sessionId);
  const res = await fetch(`${BACKEND_URL}/sessions/${sessionId}/report${qs}`, { headers });
  if (!res.ok) throw new ApiError(`report failed: ${res.status}`, res.status);
  return res.json();
}

export async function createShareLink(sessionId: string): Promise<{ share_url: string }> {
  const res = await fetch(`${BACKEND_URL}/sessions/${sessionId}/report/share`, {
    method: "POST",
    headers: { ...authHeaders(sessionId) },
  });
  if (!res.ok) throw new Error(`share failed: ${res.status}`);
  return res.json();
}

export type PublicConfig = {
  mentor_booking_url: string;
  demo_mode: boolean;
  audio_chunk_seconds: number;
};

export async function getPublicConfig(): Promise<PublicConfig> {
  const res = await fetch(`${BACKEND_URL}/config`);
  if (!res.ok) throw new Error(`config failed: ${res.status}`);
  return res.json();
}
