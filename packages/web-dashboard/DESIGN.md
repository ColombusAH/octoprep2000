---
name: OctoPrep2000
description: AI rehearsal co-pilot — score your presentation practice like a recovery score, not a grade.
colors:
  slate-night: "#0f1419"
  raised-slate: "#1a2028"
  slate-seam: "#2a323c"
  cool-white: "#e8eef4"
  slate-fog: "#8a96a3"
  glacier-sky: "#6cc4ff"
  glacier-sky-hover: "#54b8fb"
  glacier-sky-active: "#3aa3eb"
  signal-green: "#1f9d55"
  signal-amber: "#f59e0b"
  signal-red: "#ef5858"
  signal-red-solid: "#b91c1c"
typography:
  display:
    fontFamily: "Geist Mono, ui-monospace, monospace"
    fontSize: "clamp(2.5rem, 6vw, 4rem)"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "Geist, -apple-system, sans-serif"
    fontSize: "1.75rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-0.01em"
  body:
    fontFamily: "Geist, -apple-system, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  label:
    fontFamily: "Geist, -apple-system, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "0.04em"
  data:
    fontFamily: "Geist Mono, ui-monospace, monospace"
    fontSize: "0.875rem"
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: "normal"
rounded:
  sm: "8px"
  md: "12px"
  lg: "16px"
  full: "9999px"
spacing:
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.glacier-sky}"
    textColor: "{colors.slate-night}"
    typography: "{typography.body}"
    rounded: "{rounded.sm}"
    padding: "12px 16px"
  button-primary-hover:
    backgroundColor: "{colors.glacier-sky-hover}"
  button-primary-active:
    backgroundColor: "{colors.glacier-sky-active}"
  button-secondary:
    backgroundColor: "{colors.raised-slate}"
    textColor: "{colors.cool-white}"
    typography: "{typography.body}"
    rounded: "{rounded.sm}"
    padding: "10px 16px"
  card:
    backgroundColor: "{colors.raised-slate}"
    textColor: "{colors.cool-white}"
    rounded: "{rounded.md}"
    padding: "20px"
  input:
    backgroundColor: "{colors.raised-slate}"
    textColor: "{colors.cool-white}"
    typography: "{typography.body}"
    rounded: "{rounded.sm}"
    padding: "10px 12px"
---

# Design System: OctoPrep2000

## 1. Overview

**Creative North Star: "The Recovery Score"**

OctoPrep2000 borrows its visual logic from the performance-tracker category (Whoop, Oura): a single dark instrument panel where a number you can trust matters more than decoration. The system is precise, calm, and quiet by design — it never shouts a grade and never punishes a low score with alarm-red panels. A number on a dark field, supporting data in mono type, status communicated by both color and label so nothing depends on color alone.

This system explicitly rejects the generic corporate-SaaS-dashboard look: no purple-to-blue gradients, no gray text dropped onto colored chips, no cards nested inside cards, no bounce or elastic motion, and no system-default typography (the previous build used the literal `system-ui` stack, which reads as unfinished — every other touchpoint of this product needed a deliberate typeface instead).

**Key Characteristics:**
- Near-black slate canvas, not pure black — feels like an instrument at rest, not a void.
- One accent color (glacier sky blue), used sparingly, never as a page background.
- A second typographic voice (mono) reserved for anything measured: scores, timestamps, session IDs.
- Flat by default; elevation is tonal (a lighter slate surface), not shadow-driven.

## 2. Colors

The palette is a single dark neutral ramp plus one accent and three semantic status colors — restrained, not full-palette.

### Primary
- **Glacier Sky** (#6cc4ff): the one accent. Primary buttons, links, the focus ring around the score circle, active-state UI. Never used as a fill larger than a button or ring — its rarity is what makes it feel deliberate rather than decorative.

### Neutral
- **Slate Night** (#0f1419): page background. Near-black with a cool, almost imperceptible blue cast — an instrument panel, not a void.
- **Raised Slate** (#1a2028): surface for cards, panels, inputs, the toast background. One step up from Slate Night; this step IS the elevation system (see §4).
- **Slate Seam** (#2a323c): borders and dividers only. Never used as a fill.
- **Cool White** (#e8eef4): primary text. Not pure white — keeps the cool cast consistent top to bottom.
- **Slate Fog** (#8a96a3): secondary/muted text (captions, metadata, helper copy). Must still clear 4.5:1 against Slate Night and Raised Slate; verify before reuse on a new surface.

### Status (semantic, not brand)
- **Signal Green** (#1f9d55): strengths, scores ≥80, the unlocked mentor state. Always paired with a label or icon, never color alone.
- **Signal Amber** (#f59e0b): improvements, scores 60–79, medium-severity live warnings. Default "you're not there yet" tone — not alarming.
- **Signal Red** (#ef5858): scores <60 and high-severity warnings — text and icon color. Used at low surface area (a number, an icon, a thin underline) — never as a panel background. A low score is information, not a verdict; the UI should never look like a punishment screen. (#dc2626, the initial pick, only hit 3.39:1 against Raised Slate — fails WCAG AA 4.5:1 for normal text. #ef5858 hits 4.84:1.)
- **Signal Red Solid** (#b91c1c): the one exception to "Signal Red is text/icon only" — solid fill for the End Session button specifically, paired with white text (5.54:1). A single red can't satisfy both roles: text-on-dark wants it lighter, white-text-on-fill wants it darker.

### Named Rules
**The One Accent Rule.** Glacier Sky is the only saturated color with no semantic status meaning. If a new element needs emphasis and it isn't interactive (button, link, focus state), reach for typography weight or the Raised Slate elevation step before reaching for color.

**The Status-Plus-Label Rule.** Every status color (green/amber/red) ships with an icon or text label in the same component. No color-only signal, anywhere — this is load-bearing for the PRD's accessibility requirement, not a nice-to-have.

## 3. Typography

**Display/Data Font:** Geist Mono (fallback: ui-monospace, monospace)
**Body/Headline Font:** Geist (fallback: -apple-system, sans-serif)

**Character:** A geometric grotesk paired with its own monospace sibling — one family, two voices. Prose and UI chrome read in Geist; anything measured (the hero score, timestamps, session IDs, per-category point totals) reads in Geist Mono, so numbers feel like instrument readouts rather than typeset copy. Replaces the previous `ui-sans-serif, system-ui` stack everywhere — that stack is the literal definition of unfinished.

### Hierarchy
- **Display** (700, `clamp(2.5rem, 6vw, 4rem)`, line-height 1, Geist Mono): the hero overall score only ("87"). Letter-spacing −0.02em so large mono digits don't drift apart.
- **Headline** (600, 1.75rem, line-height 1.2, Geist): page titles, the score-panel section titles ("Voice & Delivery").
- **Body** (400, 1rem, line-height 1.5, Geist): all prose — insight messages, form labels, helper text. Cap line length at 65–75ch inside insight panels.
- **Label** (600, 0.75rem, letter-spacing 0.04em, uppercase, Geist): column headers ("Strengths", "Improvements"), small metadata tags.
- **Data** (500, 0.875rem, line-height 1.4, Geist Mono): timestamps ("→ 2:14"), slide references ("→ slides 4, 6"), session IDs.

### Named Rules
**The Two-Voice Rule.** Prose is Geist; anything that is a measurement (a score, a timestamp, a slide number, a session ID) is Geist Mono. If you're not sure which a piece of text is, ask whether it was computed — computed values get mono.

## 4. Elevation

Flat by default, tonal instead of shadow-driven: depth comes from the Slate Night → Raised Slate step, not from `box-shadow`. This matches the "instrument, not decoration" personality — shadows read as a UI trying to look impressive; a clean tonal step reads as precise.

### Shadow Vocabulary
- **Interactive lift** (`box-shadow: 0 1px 2px rgba(0,0,0,0.3)`): the *only* shadow in the system. Applied only on `:hover`/`:focus-visible` for buttons and the share-link affordance — a response to interaction, never present at rest.

### Named Rules
**The Flat-At-Rest Rule.** No surface has a shadow in its default state. Shadows exist solely as hover/focus feedback on interactive elements, and disappear the instant the pointer/focus leaves.

## 5. Components

### Buttons
- **Shape:** 8px radius (`rounded.sm`).
- **Primary:** Glacier Sky background, Slate Night text, 600 weight, 12px/16px padding. This is the only place the accent fills a solid background.
- **Secondary/Ghost:** Raised Slate background, Cool White text, Slate Seam 1px border. Used for "Copy share link", "Show live feedback" toggle, anything non-primary.
- **Hover/Focus:** background steps to Glacier Sky Hover (#54b8fb) / darkens for secondary buttons to a lighter Slate Seam tint; add the Interactive Lift shadow; no transform/scale (no bounce).
- **Destructive (End Session):** Signal Red Solid (#b91c1c) background, Cool White text (5.54:1) — the one button allowed to use a status color as a fill, because ending the recording is a deliberate, infrequent, consequential action. Uses the Solid shade, not text-Signal-Red, since white text on the lighter text-shade red fails AA.

### Cards / Panels
- **Corner Style:** 12px radius (`rounded.md`).
- **Background:** Raised Slate on Slate Night — the only elevation cue (§4).
- **Shadow Strategy:** none at rest (Flat-At-Rest Rule).
- **Border:** none by default; a 1px Slate Seam border only where two panels sit edge-to-edge with no gap.
- **Internal Padding:** 20–24px (`rounded` aside, use `spacing.lg`).
- **Never nest a card inside a card.** A panel's strength/improvement columns are plain flex columns, not sub-cards.

### Inputs / Fields
- **Style:** Raised Slate background, Slate Seam 1px border, 8px radius, Cool White text, Slate Fog placeholder (verified ≥4.5:1, not the default muted gray).
- **Focus:** border shifts to Glacier Sky, no glow/ring blur — a clean 1px color change reads as precise, not decorative.
- **Error/Disabled:** error border uses Signal Red + an inline icon/text (never red border alone); disabled drops opacity to 0.5 and removes the cursor pointer.

### The Score Ring (signature component)
- A circular instrument readout, not a progress bar: 160px circle, 8px stroke, stroke color = status color for the overall score band (green ≥80 / amber 60–79 / red <60), center text in Display typography (Geist Mono, 700).
- No gradient stroke, no drop shadow, no rotating/spinning entrance — it resolves into place once (a brief stroke-draw from 0 to the score value, ease-out-quart, ~600ms), then stays static. This is the one moment of choreographed motion in the whole system; everywhere else motion is purely responsive (§6).

### Toasts
- Raised Slate background, left edge uses a **full 1px Slate Seam border**, not a colored stripe (the system has no side-stripe-border components — severity is carried by an inline icon, not a colored bar). Slide in from the right, ease-out-quart, no bounce; auto-dismiss after 5s per PRD.

## 6. Do's and Don'ts

### Do:
- **Do** keep the dark Slate Night → Raised Slate tonal step as the only elevation mechanism (Flat-At-Rest Rule).
- **Do** render every measured value (scores, timestamps, slide numbers, session IDs) in Geist Mono (Two-Voice Rule).
- **Do** pair every status color with an icon or text label, with no exceptions (Status-Plus-Label Rule).
- **Do** use ease-out-quart/expo for all transitions, with a `prefers-reduced-motion` fallback that drops to an instant or cross-fade state change.
- **Do** treat a low score as information: Signal Red appears on numbers/icons only, never as a panel or page background.

### Don't:
- **Don't** use Inter, Arial, or the literal `system-ui` font stack anywhere in this product (PRODUCT.md anti-reference).
- **Don't** use a purple-to-blue gradient, or any gradient text (PRODUCT.md anti-reference; also an Impeccable absolute ban).
- **Don't** place gray (Slate Fog) text on any of the three status colors — use Slate Night or Cool White depending on the status color's lightness, whichever clears 4.5:1.
- **Don't** nest a card/panel inside another card/panel (PRODUCT.md anti-reference).
- **Don't** use bounce or elastic easing on any transition or entrance (PRODUCT.md anti-reference).
- **Don't** use a colored side-stripe border (`border-left`/`border-right` as an accent) on toasts, alerts, or list items — use a full border, background tint, or icon instead.
- **Don't** make the product feel like a generic corporate SaaS dashboard, a cartoon/gamified mascot experience, or a punitive grading screen (PRODUCT.md anti-references) — the test is the Recovery Score North Star: would Whoop or Oura ship this screen?
