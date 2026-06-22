# Product

## Register

product

## Users
Primary: presenters rehearsing a tech talk alone in front of a webcam, often anxious about being judged — engineers preparing a conference talk, or developers prepping a demo/architecture review with limited prep time (PRD personas: "The Conference Speaker", "The Internal Presenter"). They upload a deck, rehearse once, then read a scored report alone afterward — no one is in the room coaching them in real time.

Secondary: Hackathon judges watching the live demo. They never see the recording flow up close for long — what they see is the score report screen, briefly, while the presenter narrates. It carries the most weight per second of any screen.

## Product Purpose
An always-on AI rehearsal co-pilot: upload a slide deck, rehearse live on camera, get a 4-vector scored report (voice 30%, body 30%, slides 20%, content 20%) with timestamped feedback. A score ≥80 unlocks booking a 1-on-1 with a Tikal mentor. Success looks like a presenter trusting the score enough to act on the specific improvements it names, rather than dismissing it as an arbitrary AI grade.

## Brand Personality
Clinical performance coach. Reference: Whoop / Oura — the score is treated as serious, useful personal-performance data, not a cheerful gamified badge and not a harsh grade. Precise. Calm. Encouraging through clarity, not through cheerleading copy.

Tone in copy: state facts and specific next actions ("you're 6 points from unlocking a mentor session — improve eye contact on slides 4-6") rather than generic praise or generic criticism.

## Anti-references
- Generic corporate SaaS dashboard look (the thing this product should explicitly not resemble despite being an app-UI/dashboard register).
- Inter / Arial / system-default fonts.
- Purple-to-blue gradients.
- Gray text on colored backgrounds.
- Cards nested inside cards.
- Bounce / elastic easing on any motion.
- Cartoon mascots or gamified badge/streak treatments (Duolingo's tone without Duolingo's visual gamification).
- Punitive framing in copy or color (e.g. all-red failure states) — a low score is information, not a verdict.

## Design Principles
- **Score as information, not judgment.** Present feedback the way a recovery-score app does: precise numbers, specific timestamps, no punitive color or copy.
- **Calm under pressure.** The presenter using this is already anxious about being judged; the UI should lower arousal, not add to it.
- **Earn trust through restraint.** Precision (real numbers, real timestamps, real slide references) builds more credibility than decoration or gamification.
- **Speed is part of the experience.** Per PRD: "Speed over polish — the demo must feel live. Latency is a UX metric." Motion and visual richness must never read as, or cause, perceived latency.
- **Demo-day spotlight.** Only the 3 screens visible in the live judged demo (upload, recording, report) earn full polish investment; the report screen carries the most weight.

## Accessibility & Inclusion
WCAG AA contrast minimum. Color is never the sole differentiator — icons and labels always accompany color coding (existing PRD §10 rule, e.g. lock/unlock state, strength/improvement panels, score color bands). No additional accessibility requirements scoped for this hackathon (single-day build).
