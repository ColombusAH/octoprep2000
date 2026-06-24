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
    topic: "Agentic Engineering: Patterns, Architectures",
    overall_score: 91,
    voice_score: 90,
    body_score: 88,
    slide_score: 92,
    content_score: 94,
    mentor_unlocked: true,
    insights: [
      {
        category: "voice",
        type: "STRENGTH",
        message: "Confident, well-modulated pace through the ReAct loop and planner-executor walkthrough — technical terms landed clearly.",
      },
      {
        category: "voice",
        type: "STRENGTH",
        message: "Strategic pauses before each new architecture diagram gave the audience time to absorb it.",
      },
      {
        category: "voice",
        type: "IMPROVEMENT",
        message: "Volume dipped slightly while comparing multi-agent orchestration trade-offs.",
        timestamps: [276000],
      },
      {
        category: "body",
        type: "STRENGTH",
        message: "Open stance with purposeful hand gestures while mapping the agent-tool-environment loop.",
      },
      {
        category: "body",
        type: "STRENGTH",
        message: "Strong, sustained eye contact with the camera through the live multi-agent demo segment.",
      },
      {
        category: "body",
        type: "IMPROVEMENT",
        message: "Stepped slightly out of frame while sketching the orchestrator-worker diagram.",
        timestamps: [198000],
      },
      {
        category: "slide",
        type: "STRENGTH",
        message: "Planner → executor → tool-call loop diagram was clean and easy to follow at a glance.",
      },
      {
        category: "slide",
        type: "STRENGTH",
        message: "Consistent visual language across every pattern comparison (ReAct vs. Plan-and-Execute vs. multi-agent).",
      },
      {
        category: "slide",
        type: "IMPROVEMENT",
        message: "The RAG pipeline diagram packed a few too many components into one frame.",
        slides: [9],
      },
      {
        category: "content",
        type: "STRENGTH",
        message: "Precise, accurate framing of the ReAct (Reason+Act) pattern and when to reach for it over a single-shot prompt.",
      },
      {
        category: "content",
        type: "STRENGTH",
        message: "Strong comparative analysis of planner-executor vs. multi-agent orchestrator architectures, including cost and latency trade-offs.",
      },
      {
        category: "content",
        type: "STRENGTH",
        message: "Clearly tied agent memory architectures (short-term context vs. long-term vector store) back to real production constraints.",
      },
      {
        category: "content",
        type: "IMPROVEMENT",
        message: "Could have spent one more beat on evaluation and guardrails for autonomous agents — a likely audience question.",
      },
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
