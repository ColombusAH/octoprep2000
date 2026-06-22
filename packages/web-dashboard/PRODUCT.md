# Product

## Register

product

## Users
Primary: presenters rehearsing a tech talk alone in front of a webcam, often anxious about being judged — engineers preparing a conference talk, or developers prepping a demo/architecture review with limited prep time (PRD personas: "The Conference Speaker", "The Internal Presenter"). They upload a deck, rehearse once, then read a scored report alone afterward — no one is in the room coaching them in real time.

Secondary: Hackathon judges watching the live demo. They never see the recording flow up close for long — what they see is the score report screen, briefly, while the presenter narrates. It carries the most weight per second of any screen.

## Product Purpose
An always-on AI rehearsal co-pilot: upload a slide deck, rehearse live on camera, get a 4-vector scored report (voice 30%, body 30%, slides 20%, content 20%) with timestamped feedback. A score ≥80 unlocks booking a 1-on-1 with a Tikal mentor. Success looks like a presenter trusting the score enough to act on the specific improvements it names, rather than dismissing it as an arbitrary AI grade.

## Brand Personality
**Y2K broadcast deck.** Reference: `docs/presentation/octoprep2000-pitch.html`, the Fuse Day pitch deck — VHS tracking, CRT scanlines, a blinking REC dot, a navy instrument panel with one warm hero accent. The dashboard now wears the same identity as the thing being pitched, instead of a separate "clinical tool" register sitting next to a flashy deck.

**This replaces the earlier Whoop/Oura "clinical performance coach" personality.** That read was right for a single high-stakes score screen with no other context. Once the dashboard grew a persistent shell — sidebar, membership tier, a wallet, an archive, a leaderboard — the brief became "look like the deck," and clinical restraint stopped being the honest choice. See DESIGN.md §1 and §7 for the full rationale and what specifically flipped.

**One thing does not flip:** the *content* of the score report — the actual insight copy, timestamps, and slide references — stays factual and non-punitive. The chrome around it (wallet, tier badge, archive, leaderboard) is deliberately showy and gamified; the score itself is still data a presenter can trust, not a cheerful badge. Tone in the report's insight copy is unchanged: state facts and specific next actions ("you're 6 points from unlocking a mentor session — improve eye contact on slides 4-6") rather than generic praise or criticism.

## Anti-references
- Generic corporate SaaS dashboard look that ignores the deck's identity — flat dark-mode-default with no broadcast chrome would be a regression, not a safe choice.
- Inter / Arial / system-default fonts, or the Geist pairing from the prior iteration — Tektur / Chakra Petch / Space Mono only.
- Purple-to-blue gradients, or gradient text anywhere.
- Gray text on colored backgrounds, or any alpha-blended "dim" value used as functional text (DESIGN.md's Solid-Text Rule).
- Cards nested inside cards.
- Bounce / elastic easing on any motion — **this ban survives the pivot unchanged.** Y2K showmanship here is confident ease-out, not springy; gamification changed, the easing curve didn't.
- Soft, pastel, "cute mascot" gamification (Duolingo-style illustrated badges) — the gamification here is broadcast/HUD-styled (tier badges, mono labels, CRT chrome), not cartoon.
- Literal 8-bit/pixel-art retro — this is VHS/CRT Y2K (Tektur, scanlines, tracking rolls), not arcade pixel-art; don't conflate the two retro lanes.
- Presenting a mock/demo-only screen as if it were real functionality — every pure-visual nav item carries a "DEMO" tag (see DESIGN.md §6 Sidebar).
- Punitive framing in the score report's copy or color (e.g. all-red failure states) — a low score is still information, not a verdict, even though the chrome around it is louder now.

## Design Principles
- **Score as information, not judgment.** Unchanged: the report's insight copy stays precise, specific, and free of punitive color or language, regardless of how gamified the surrounding shell is.
- **Decorate the chrome, not the critical path.** The sidebar, archive, and tab-transitions can be loud and animated. Starting/ending a recording and reading the score stay snappy and free of decorative motion that could read as, or cause, latency (DESIGN.md's No-Loop-On-Critical-Path Rule).
- **Earn trust through precision, not restraint.** The old principle conflated "trustworthy" with "undecorated." The dashboard can look like a Y2K broadcast deck and still earn trust — what matters is that the score itself stays made of real numbers, real timestamps, real slide references.
- **Speed is part of the experience.** Per PRD: "Speed over polish — the demo must feel live. Latency is a UX metric." Unchanged — motion and visual richness must never read as, or cause, perceived latency.
- **Demo-day spotlight.** The 3 screens in the live judged demo (start, recording, report) still earn the deepest polish investment; the persistent shell (sidebar, home) is the next tier; pure-mock nav items (leaderboard, achievements, settings) get a believable but lighter-touch pass.

## Accessibility & Inclusion
WCAG AA contrast minimum — **unchanged through the Y2K pivot**, re-verified against the new palette (DESIGN.md §2 lists computed ratios for every text/background pairing). Color is never the sole differentiator — icons and labels always accompany color coding (existing PRD §10 rule, e.g. lock/unlock state, strength/improvement panels, score color bands). No additional accessibility requirements scoped for this hackathon (single-day build).
