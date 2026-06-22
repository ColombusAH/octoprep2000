import type { ReportData } from "~/components/ScoreCard";

/**
 * Dev-only fixtures for iterating on the report screen without a live rehearsal.
 * Wired in via ?mock=<key> on /session/$id/report, gated by import.meta.env.DEV.
 */
export const MOCK_REPORTS: Record<string, ReportData> = {
  unlocked: {
    overall_score: 87,
    voice_score: 88,
    body_score: 91,
    slide_score: 82,
    content_score: 86,
    mentor_unlocked: true,
    insights: [
      { category: "voice", type: "STRENGTH", message: "Clear, steady pace throughout the talk." },
      { category: "voice", type: "IMPROVEMENT", message: "A few filler words crept in mid-talk.", timestamps: [134000, 312000] },
      { category: "body", type: "STRENGTH", message: "Strong eye contact with the camera." },
      { category: "slide", type: "STRENGTH", message: "Clean, uncluttered slide layouts." },
      { category: "slide", type: "IMPROVEMENT", message: "Code sample text was too small to read.", slides: [4] },
      { category: "content", type: "STRENGTH", message: "Accurately described React 19's new hooks." },
    ],
  },
  locked: {
    overall_score: 64,
    voice_score: 70,
    body_score: 58,
    slide_score: 60,
    content_score: 68,
    mentor_unlocked: false,
    insights: [
      { category: "voice", type: "IMPROVEMENT", message: "Speaking pace was too fast in the opening minute.", timestamps: [12000, 45000] },
      { category: "body", type: "IMPROVEMENT", message: "Eye contact dropped during slide transitions.", timestamps: [88000] },
      { category: "slide", type: "IMPROVEMENT", message: "Slide 6 had too much text to read while listening.", slides: [6] },
      { category: "content", type: "STRENGTH", message: "Good grasp of the core concept." },
      { category: "content", type: "IMPROVEMENT", message: "Missed mentioning a key tradeoff judges may ask about." },
    ],
  },
  "no-camera": {
    overall_score: 71,
    voice_score: 75,
    body_score: null,
    slide_score: 69,
    content_score: 70,
    mentor_unlocked: false,
    insights: [
      { category: "voice", type: "STRENGTH", message: "Confident, well-paced delivery." },
      { category: "slide", type: "IMPROVEMENT", message: "Slide 2 had a typo in the title.", slides: [2] },
      { category: "content", type: "STRENGTH", message: "Solid technical accuracy throughout." },
    ],
  },
  perfect: {
    overall_score: 96,
    voice_score: 97,
    body_score: 95,
    slide_score: 94,
    content_score: 98,
    mentor_unlocked: true,
    insights: [
      { category: "voice", type: "STRENGTH", message: "Excellent pacing and vocal variety throughout." },
      { category: "body", type: "STRENGTH", message: "Commanding presence, steady eye contact." },
      { category: "slide", type: "STRENGTH", message: "Clean, well-paced slide design." },
      { category: "content", type: "STRENGTH", message: "Deep, accurate technical coverage." },
    ],
  },
  "rough-cut": {
    overall_score: 41,
    voice_score: 44,
    body_score: 38,
    slide_score: 45,
    content_score: 39,
    mentor_unlocked: false,
    insights: [
      { category: "voice", type: "IMPROVEMENT", message: "Frequent long pauses broke the flow.", timestamps: [22000, 96000, 201000] },
      { category: "body", type: "IMPROVEMENT", message: "Looked away from camera for most of the talk." },
      { category: "slide", type: "IMPROVEMENT", message: "Slides 1-3 had dense walls of text.", slides: [1, 2, 3] },
      { category: "content", type: "IMPROVEMENT", message: "Missed the core tradeoff the audience asked about." },
    ],
  },
};

export const MOCK_CONFIG = {
  mentor_booking_url: "https://tikal.co/mentor-booking",
  demo_mode: true,
  audio_chunk_seconds: 2,
};
