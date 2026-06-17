/**
 * Mirrors backend Pydantic schemas in agents/schemas.py.
 * Used by web-dashboard + (future) Chrome Extension to type WS payloads.
 *
 * Keep in sync with packages/backend/agents/schemas.py.
 */

export type Severity = "LOW" | "MEDIUM" | "HIGH";

export type VideoEventType =
  | "EYE_CONTACT_LOST"
  | "POSTURE_ISSUE"
  | "OUT_OF_FRAME"
  | "GESTURE_CLOSED"
  | "FACE_NOT_DETECTED"
  | "FACE_TILTED"
  | "SMILING_STRONG";

export type AudioWarningType =
  | "FILLER_WORDS"
  | "PACING_TOO_FAST"
  | "PACING_TOO_SLOW"
  | "STALE_SLIDE";

export type FindingType = "STRENGTH" | "IMPROVEMENT";
export type InsightCategory = "voice" | "body" | "slide" | "content";

export interface FeedbackEvent {
  type: VideoEventType | AudioWarningType | "REPORT_READY" | "FALLBACK_ACTIVATED" | "CONTENT_READY";
  severity?: Severity;
  message?: string;
  timestamp_ms?: number;
  session_id?: string;
}

export interface Insight {
  category: InsightCategory;
  type: FindingType;
  message: string;
  timestamps?: number[];
  slides?: number[];
}

export interface ReportData {
  session_id: string;
  overall_score: number;
  voice_score: number;
  body_score: number | null;
  slide_score: number;
  content_score: number;
  insights: Insight[];
  mentor_unlocked: boolean;
  generated_at: string;
}

export interface CreateSessionResponse {
  session_id: string;
  access_token: string;
}
