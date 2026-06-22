---
name: OctoPrep2000
description: AI rehearsal co-pilot — Y2K broadcast-deck dashboard shell wrapped around a calm, factual score report.
colors:
  void: "#060d1a"
  navy: "#0a1e35"
  navy-2: "#0d2742"
  navy-3: "#14304a"
  teal: "#4dd4cc"
  orange: "#ff7a1a"
  orange-hover: "#ff8c3d"
  orange-d: "#e06a0f"
  white: "#ffffff"
  pearl: "#e8f4ff"
  ash: "#9fb3c9"
  dim: "rgba(232,244,255,0.6)"
  green: "#2ed573"
  amber: "#f5c518"
  red: "#ff6b86"
  red-solid: "#c81e3a"
typography:
  display:
    fontFamily: "Tektur, sans-serif"
    fontSize: "clamp(1.75rem, 3vw, 2.5rem)"
    fontWeight: 700
    lineHeight: 1.05
    letterSpacing: "-0.015em"
  headline:
    fontFamily: "Tektur, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.01em"
  body:
    fontFamily: "Chakra Petch, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  label:
    fontFamily: "Space Mono, ui-monospace, monospace"
    fontSize: "0.75rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "0.14em"
  data:
    fontFamily: "Space Mono, ui-monospace, monospace"
    fontSize: "0.875rem"
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: "normal"
rounded:
  sm: "0.3rem"
  md: "0.4rem"
  lg: "0.5rem"
  full: "9999px"
spacing:
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.orange}"
    textColor: "{colors.void}"
    typography: "{typography.body}"
    rounded: "{rounded.lg}"
    padding: "12px 16px"
  button-primary-hover:
    backgroundColor: "{colors.orange-hover}"
  button-primary-active:
    backgroundColor: "{colors.orange-d}"
  button-secondary:
    backgroundColor: "{colors.navy}"
    textColor: "{colors.pearl}"
    typography: "{typography.body}"
    rounded: "{rounded.lg}"
    padding: "10px 16px"
  card:
    backgroundColor: "{colors.navy-2}"
    textColor: "{colors.pearl}"
    rounded: "{rounded.lg}"
    padding: "20px"
  input:
    backgroundColor: "transparent"
    textColor: "{colors.pearl}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: "10px 12px"
---

# Design System: OctoPrep2000

## 1. Overview

**Creative North Star: "The Broadcast Deck"**

OctoPrep2000's dashboard now shares its visual identity with `docs/presentation/octoprep2000-pitch.html`, the Fuse Day pitch deck: a Y2K / early-2000s broadcast aesthetic — VHS tracking, CRT scanlines, a blinking REC dot, corner-bracket HUD chrome — built on a navy instrument-panel base with one warm hero accent (orange) and a structural chrome accent (teal).

**This deliberately replaces the previous "Recovery Score" north star** (Whoop/Oura-style clinical restraint, no gamification, no bounce). That system was the right call for a screen with no surrounding product context; once the dashboard grew a persistent shell — sidebar, membership tier, a wallet, an archive, mock nav items — the brief shifted to match the deck's own showmanship: the product should *look* like the thing being pitched. The pivot is sanctioned, not drift: §6 documents exactly which old rules flipped and why.

**Key Characteristics:**
- Near-black void canvas with a raised navy step (sidebar) and a second raised step (cards) — same tonal-elevation logic as before, now under a warmer name.
- Two accent roles instead of one: **teal** is structural/chrome-only (borders, focus rings, HUD labels, icons) and never fills a surface; **orange** is the single warm hero accent (primary actions, brand, the gamified wallet).
- Three typographic voices: Tektur for display/headlines, Chakra Petch for body and every interactive control, Space Mono for anything measured or HUD-styled.
- Chrome is static and cheap (grid + vignette + scanlines, no canvas, no timers) so it can stay mounted through a live recording without cost; choreographed motion (glitch, tracking-roll, boot flash) is reserved for one-shot moments, never infinite loops on a working screen.

## 2. Colors

Two accents instead of one, plus a status vocabulary tuned to read clearly against both background steps.

### Primary
- **Orange** (`--orange` #ff7a1a): the one hero accent — primary buttons, the wallet number, brand moments. Solid-fill orange always pairs with `--void` text (7.5:1+ contrast); never gray-on-orange.
- **Teal** (`--teal` #4dd4cc): chrome only — borders, focus rings, icons, HUD-style mono labels ("ONLINE", "TAPE 004"). Verified ≥8:1 against both `--void` and `--navy-2`, so it's safe for small mono labels, but it never carries a primary CTA — that's orange's job.

### Neutral
- **Void** (`--void` #060d1a): page background.
- **Navy** (`--navy` #0a1e35): the sidebar / second neutral layer (product register's "cooler second layer for chrome").
- **Navy 2** (`--navy-2` #0d2742): raised surface — cards, popovers, inputs' implicit background.
- **Navy 3** (`--navy-3` #14304a): hover/active tint one step above Navy 2.
- **Pearl** (`--pearl` #e8f4ff): primary text. 17.4:1 on void, 13.6:1 on navy-2.
- **Ash** (`--ash` #9fb3c9): secondary/muted text — a **solid** color, ≥7:1 on both void and navy-2.
- **Dim** (`--dim` rgba(232,244,255,0.6)): decorative HUD chrome only (eyebrow opacity, atmosphere). **Never used for functional text** — see the Solid-Text Rule below; this is the one place the deck's own values don't transfer directly.

### Status (semantic, distinct from hero orange)
- **Green** (`--green` #2ed573): strengths, scores ≥80, mentor-unlocked. ≥7.8:1 on both surfaces.
- **Amber** (`--amber` #f5c518): improvements, scores 60–79. ≥9.3:1 on both surfaces.
- **Red** (`--red` #ff6b86): scores <60, high-severity warnings — text/icon shade, ≥5.1:1 on navy-2.
- **Red Solid** (`--red-solid` #c81e3a): the one destructive-button fill (End Session), white text at 5.67:1.

### Named Rules
**The Solid-Text Rule (new).** `--dim` and any other alpha-blended pitch-deck color are decorative atmosphere values, calibrated for a fixed-stage slide, not for arbitrary UI backgrounds. Any text that must clear WCAG body contrast uses a **solid** token (`--pearl`, `--ash`, a status color) — never an alpha value. This is why the dashboard has `--ash` where the deck only has `--dim`.

**The Two-Accent Rule.** Teal is structural, orange is the hero. If new chrome needs a saturated accent and it's not a primary action, reach for teal; if it's a primary action or the one moment of warmth on a screen, reach for orange. Never both as fills on the same component.

**The Status-Plus-Label Rule** *(carried over, unchanged)*. Every status color ships with an icon or text label in the same component — survives the pivot per the brief's accessibility constraint.

## 3. Typography

**Display:** Tektur (weights 500/700/900) — hero numbers-adjacent moments, h1/h2 page titles, `CardTitle`, section headings. **Never** on a button, nav label, form label, or measured value — product register bans display fonts on functional UI text, and Tektur at small sizes loses legibility fast.
**Body:** Chakra Petch (300–700) — all prose, every interactive control: buttons, nav items, form labels, descriptions. This is the only voice closest readers should ever parse a control's hit target as English text.
**Data / HUD:** Space Mono (400/700) — anything computed or measured (scores, timestamps, slide refs, session IDs, the wallet balance) **and** HUD-style chrome labels (eyebrows, "TAPE 004", "ONLINE", category labels like "Strengths"/"Improvements"). Mono now carries two related but distinct jobs — see the rule below.

### Hierarchy
- **Display**: `clamp(1.75rem, 3vw, 2.5rem)`, 700, Tektur, letter-spacing −0.015em. Page-level h1s only.
- **Headline**: 1.125rem, 700, Tektur. Component-level titles (`CardTitle`, "Voice & Delivery" panel headers, "Mentor unlocked/locked").
- **Body**: 1rem, 400, Chakra Petch. Cap prose at 65–75ch.
- **Label**: 0.75rem, 600, Space Mono, uppercase, 0.14em tracking. HUD-style section labels.
- **Data**: 0.875rem, 500, Space Mono. Scores, timestamps, IDs.

### Named Rules
**The Three-Voice Rule** *(supersedes the old Two-Voice Rule)*. Display is for headings only. Body is for prose and every functional control. Mono is for anything computed *or* anything styled as HUD chrome. If you're labeling a button, a nav item, or a form field — that's Body, even if the brand feels mono-coded; functional text must stay scannable at speed.

## 4. Elevation & Chrome

Tonal elevation survives the pivot (Void → Navy → Navy-2 → Navy-3), but the system now layers static broadcast-deck atmosphere on top: a low-opacity teal grid, a radial vignette, and CRT scanlines (`.chrome-grid` / `.chrome-vignette` / `.chrome-scanlines` in `app/styles.css`). All three are static CSS — no canvas redraw, no interval timers — so they're cheap enough to stay mounted through a live recording without adding perceived latency.

**Corner brackets** (`<CornerBrackets />`) are the dashboard's signature chrome motif, lifted from the deck's `.bracket` corners: four 2px teal hairlines at 50% opacity on the corners of a `relative` panel. Applied to cards, the video frame, and interactive home tiles — never animated, never blocking content.

### Shadow / Glow Vocabulary
- **Interactive lift** *(carried over)*: `0 1px 2px rgba(0,0,0,0.3)` on hover/focus for buttons — the only at-rest-absent shadow.
- **Score glow** (new, deliberate second exception): the Score Ring's stroke now carries a `drop-shadow(0 0 6px <status-color>)` matching its own color — a CRT-phosphor glow, not decoration for decoration's sake. Two exceptions to "flat at rest" is the ceiling; a third needs a real reason.

### Named Rules
**The Flat-At-Rest Rule** *(amended)*: no surface has a shadow at rest **except** the Score Ring's signature glow. Everything else still earns its shadow only on hover/focus.

## 5. Motion

Lifted from the deck, restrained for a working tool: chrome gets choreography, the recording critical path does not.

- **Ease standard** (`--ease-standard`, `cubic-bezier(0.16,1,0.3,1)`): ease-out-quint for transitions and entrances — **no bounce or elastic easing**, this constraint survives the pivot unchanged.
- **Panel transitions**: route changes fade/slide up (`motion-safe:animate-in fade-in slide-in-from-bottom-2`, 300ms) — feedback that the tab-like panel changed, not an orchestrated load sequence.
- **REC dot** (`.rec-dot`): hard on/off blink (`step-end`, 1s) — literal VHS REC blink, not a smooth pulse. Always paired with a "REC" text label.
- **Glitch title** (`.glitch-text`): one-shot per mount (8s keyframe, plays once, no infinite loop) — reserved for the sidebar wordmark on initial load only. A dashboard a presenter stares at for minutes cannot repeat a glitch every 8 seconds; the deck can, because no one watches one slide that long.
- **Boot flash** (`<BootFlash />`): a ~650ms color-bar flash on first hard load only, `pointer-events-none`, never blocks interaction, skipped under reduced motion. Does not replay on client-side navigation (it lives in the shell, which doesn't remount).
- **Tracking-roll** (`.tracking-roll`): the CRT sweep, reserved for deliberate one-shot triggers (e.g. a future panel-transition flourish) — never a randomized interval timer like the deck's ambient version. Randomized "ambient" decoration belongs on a slide nobody is trying to read for 10 minutes, not a tool.

### Named Rules
**The No-Loop-On-Critical-Path Rule (new).** The recording screen (`session.$id.tsx`) gets static chrome only — corner brackets, a static REC blink paired with a label. No canvas noise, no randomized tracking-roll, nothing that runs continuously while a rehearsal is being captured. Decorate the chrome; never the thing the presenter is staring at while talking.

**Reduced motion** *(carried over, unchanged)*: every keyframe-driven element (`recBlink`, `titleGlitch`, `trackingRoll`, `bootBars`) has a `prefers-reduced-motion: reduce` fallback that disables the animation outright, consistent with the project's existing `motion-safe:`/`motion-reduce:` convention.

## 6. Components

### Buttons *(token values changed, structure unchanged)*
- **Primary**: Orange background, Void text, 600 weight. Hover → Orange Hover (#ff8c3d); active → Orange-D (#e06a0f).
- **Secondary/Ghost**: Navy background, Pearl text, teal-tinted hairline border.
- **Destructive (End Session)**: Red Solid (#c81e3a) fill, white text (5.67:1) — unchanged rationale: a deliberate, infrequent, consequential action earns the one status-as-fill exception.

### Cards / Panels
- Navy-2 background, teal-tinted hairline border (`rgba(77,212,204,0.22)`), `--radius: 0.5rem` (slightly boxier than the old 0.75rem — a console, not a soft app tile).
- **Never nest a card inside a card** *(carried over, unchanged)*.
- Score-category panels and the hero score card now carry `<CornerBrackets />` — the one piece of "every-pixel" decoration that earned its place because the report screen is the highest-stakes screen in the live demo.

### The Score Ring *(signature component, unchanged behavior)*
- Same 160px circle / 8px stroke / one-time stroke-draw entrance as before. New: a `drop-shadow` glow in the score's own status color (§4).

### Sidebar (new)
- Navy background, teal-tinted border, persistent across all routes (mounted in `__root.tsx`, not per-route).
- Avatar placeholder → dashed-teal square, mono "#OP-2000" tag.
- Status row: green Wifi icon + "ONLINE" mono label (icon+label, never color alone) plus a "GOLD OPERATOR" tier badge — orange-tinted pill, mono, tracked.
- Wallet ("Tape Credits"): Space Mono number, briefly scales + flashes orange on increment (`justIncreased` in `useWallet()`), 900ms, ease-standard.
- Nav items: active state = Navy-3 fill + orange icon; mock-only items carry a small "DEMO" mono tag so it's honest about what's wired up.

### Reports Archive — "Tape Rack" (new)
- A flat list of "tape" rows (mono `TAPE 00X` id, topic in Tektur, date in mono, score in its status color, lock/unlock icon) — teletext-listing density rather than a card grid, per the brief's VHS-rack framing. Clicking a row routes to `/session/$id/report?mock=<key>`, reusing the existing dev-fixture convention in `app/lib/mockReportData.ts`.

### Toasts *(unchanged structure, retuned voice)*
- Same shape as before (full border, no colored stripe — the side-stripe ban is unchanged). Message text now renders in Space Mono — toasts are live telemetry, not prose.

## 7. Do's and Don'ts

### Do:
- **Do** keep teal structural-only and orange as the single hero fill — the Two-Accent Rule.
- **Do** use a solid color (`--ash`, `--pearl`, a status color) for any text that needs guaranteed contrast — never `--dim` or another alpha value (Solid-Text Rule).
- **Do** keep Tektur off buttons, nav labels, form labels, and data — Body and Mono carry all functional text (Three-Voice Rule).
- **Do** keep the dashboard's gamified chrome (wallet, tier badge, archive, leaderboard, achievements) honestly labeled as demo/mock where it isn't backed by real data.
- **Do** keep every status color paired with an icon or label — unchanged accessibility floor.
- **Do** keep chrome (grid/vignette/scanlines/brackets) static and cheap enough to run through a live recording.

### Don't:
- **Don't** reach for bounce or elastic easing on any transition — *the no-bounce rule survives the pivot even though gamification doesn't*. Y2K showmanship reads as confident, snappy ease-out, not springy.
- **Don't** run a continuous/randomized decorative loop (canvas noise, random tracking-roll, infinite glitch) on a screen the user is actively working in, especially the recording screen — see the No-Loop-On-Critical-Path Rule.
- **Don't** use Tektur anywhere a user reads it as a control rather than a heading.
- **Don't** place `--ash`-on-status-color or any low-contrast pairing — same AA floor as before, new palette.
- **Don't** use a colored side-stripe border on toasts, alerts, or list/archive rows — full border or background tint only, unchanged ban.
- **Don't** nest a card/panel inside another card/panel — unchanged ban.
- **Don't** silently mix mock and real data — every pure-visual nav item (Leaderboard, Achievements, Settings) carries a "DEMO" tag so the live judged demo never implies a feature that isn't built.

### What changed from "The Recovery Score" (for the record)
The old system's anti-gamification and anti-bounce rules weren't wrong for what they were guarding — a single, high-stakes score screen judged in the moment. They're superseded, not violated, now that the surrounding shell is an explicit Y2K/gamified pivot: the **wallet, tier badge, leaderboard, and achievements are new, deliberate gamification** the old system explicitly banned. The bounce/elastic-easing ban is the one rule that **survives untouched** — Y2K showmanship in this deck is confident and snappy, not springy, so there was never a reason to introduce bounce even while everything else about the tone flipped.
