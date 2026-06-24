import {
  Document,
  Page,
  Text,
  View,
  StyleSheet,
  pdf,
} from "@react-pdf/renderer";
import type { ReportData } from "~/components/ScoreCard";
import {
  AI_DISCLAIMER,
  CATEGORY_META,
  buildPdfFilename,
  formatInsightRefs,
  scoreColorHex,
  type Insight,
  type InsightCategory,
} from "~/lib/reportFormatting";

const S = StyleSheet.create({
  page: { padding: 40, fontSize: 11, fontFamily: "Helvetica", color: "#111" },
  h1: { fontSize: 18, fontFamily: "Helvetica-Bold", marginBottom: 4 },
  meta: { fontSize: 10, color: "#555", marginBottom: 16 },
  box: { marginBottom: 12, padding: 12, borderWidth: 1, borderColor: "#e5e5e5" },
  score: { fontSize: 32, fontFamily: "Helvetica-Bold" },
  bold: { fontFamily: "Helvetica-Bold" },
  label: {
    fontSize: 9,
    fontFamily: "Helvetica-Bold",
    color: "#0d9488",
    marginTop: 6,
    marginBottom: 2,
  },
  row: { fontSize: 11, marginBottom: 3, paddingLeft: 6 },
  muted: { fontSize: 11, color: "#666", fontStyle: "italic" },
  disclaimer: { marginTop: 12, fontSize: 9, color: "#666" },
});

function InsightBlock({ label, items }: { label: string; items: Insight[] }) {
  return (
    <View>
      <Text style={S.label}>{label}</Text>
      {items.length === 0 ? (
        <Text style={S.muted}>—</Text>
      ) : (
        items.map((insight, idx) => (
          <Text key={idx} style={S.row}>
            • {insight.message}
            {formatInsightRefs(insight)}
          </Text>
        ))
      )}
    </View>
  );
}

function Category({
  category,
  score,
  insights,
}: {
  category: InsightCategory;
  score: number | null;
  insights: Insight[];
}) {
  const strengths = insights.filter((i) => i.type === "STRENGTH");
  const improvements = insights.filter((i) => i.type === "IMPROVEMENT");
  const notScored = score === null && insights.length === 0;

  return (
    <View style={S.box}>
      <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
        <Text style={S.bold}>{CATEGORY_META[category].title}</Text>
        {score !== null && (
          <Text style={[S.bold, { color: scoreColorHex(score) }]}>
            {Math.round(score)}/100
          </Text>
        )}
      </View>
      {notScored ? (
        <Text style={S.muted}>Not scored this session — camera was unavailable.</Text>
      ) : (
        <>
          <InsightBlock label="STRENGTHS" items={strengths} />
          <InsightBlock label="IMPROVEMENTS" items={improvements} />
        </>
      )}
    </View>
  );
}

function ReportPdf({
  sessionId,
  report,
  mentorBookingUrl,
}: {
  sessionId: string;
  report: ReportData;
  mentorBookingUrl: string;
}) {
  const delta = Math.max(0, 80 - report.overall_score);
  const byCat = (cat: InsightCategory) => report.insights.filter((i) => i.category === cat);

  return (
    <Document>
      <Page size="A4" style={S.page}>
        <Text style={S.h1}>OctoPrep2000 — Session Report</Text>
        <Text style={S.meta}>
          Session {sessionId.slice(0, 8)}… · Generated {new Date().toLocaleDateString()}
        </Text>

        <View style={S.box}>
          <Text style={[S.score, { color: scoreColorHex(report.overall_score) }]}>
            {Math.round(report.overall_score)}
          </Text>
          <Text style={S.meta}>Overall score / 100</Text>
        </View>

        <View style={S.box}>
          <Text style={S.bold}>
            {report.mentor_unlocked ? "Mentor unlocked" : "Mentor locked"}
          </Text>
          <Text style={{ marginTop: 4 }}>
            {report.mentor_unlocked
              ? `Book your 1-on-1 with a Tikal Expert: ${mentorBookingUrl}`
              : `You are ${Math.ceil(delta)} points away from unlocking a 1-on-1 session with a Tikal Expert. Review the targeted improvements below and try again.`}
          </Text>
        </View>

        <Category category="voice" score={report.voice_score} insights={byCat("voice")} />
        <Category category="body" score={report.body_score} insights={byCat("body")} />
        <Category category="slide" score={report.slide_score} insights={byCat("slide")} />
        <Category category="content" score={report.content_score} insights={byCat("content")} />

        <Text style={S.disclaimer}>{AI_DISCLAIMER}</Text>
      </Page>
    </Document>
  );
}

export async function exportReportPdf(input: {
  sessionId: string;
  report: ReportData;
  mentorBookingUrl: string;
}): Promise<void> {
  const blob = await pdf(
    <ReportPdf
      sessionId={input.sessionId}
      report={input.report}
      mentorBookingUrl={input.mentorBookingUrl}
    />,
  ).toBlob();
  const url = URL.createObjectURL(blob);
  try {
    const a = document.createElement("a");
    a.href = url;
    a.download = buildPdfFilename(input.sessionId);
    a.style.display = "none";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  } finally {
    URL.revokeObjectURL(url);
  }
}
