export type InsightCategory = "voice" | "body" | "slide" | "content";

export type Insight = {
  category: InsightCategory;
  type: "STRENGTH" | "IMPROVEMENT";
  message: string;
  timestamps?: number[];
  slides?: number[];
};

export const CATEGORY_META: Record<InsightCategory, { title: string }> = {
  voice: { title: "Voice & Delivery" },
  body: { title: "Body Language & Camera" },
  slide: { title: "Slide Quality" },
  content: { title: "Technical Content" },
};

export const AI_DISCLAIMER =
  "Content accuracy powered by AI training data. May not reflect features released after the model's training cutoff.";

export function formatTs(ms: number): string {
  const total = Math.floor(ms / 1000);
  const m = Math.floor(total / 60);
  const s = (total % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

export function scoreColorHex(score: number): string {
  if (score >= 80) return "#22c55e";
  if (score >= 60) return "#f59e0b";
  return "#ef4444";
}

export function formatInsightRefs(insight: Insight): string {
  const parts: string[] = [];
  if (insight.timestamps && insight.timestamps.length > 0) {
    parts.push(insight.timestamps.map(formatTs).join(", "));
  }
  if (insight.slides && insight.slides.length > 0) {
    parts.push(`slides ${insight.slides.join(", ")}`);
  }
  return parts.length > 0 ? ` → ${parts.join(" · ")}` : "";
}

export function buildPdfFilename(sessionId: string): string {
  const prefix = sessionId.slice(0, 8);
  const date = new Date().toISOString().slice(0, 10);
  return `octoprep-report-${prefix}-${date}.pdf`;
}
