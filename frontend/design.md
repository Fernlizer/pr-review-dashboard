# Design — PR Review Dashboard

Locked design direction for the app.

## Concept

**Living Orbit** — a private mission-control habitat for one reviewer.

The interface should feel like a quiet luxury spacecraft that is alive: dark,
expensive, precise, and breathing. The app is not a generic admin dashboard and
must not look like a flat 2000s table/card grid.

## Audience

Single operator: Sasharat / the repo owner using the service as a personal PR
review cockpit.

## Primary use

The home page is a system overview and control surface:

- overall review/polling health
- current running review status
- quick PR URL submission
- scheduler/poller visibility
- recent review signals
- risk/finding summary

## Genre

atmospheric + luxury

## Macrostructure family

- App shell: side-rail command habitat
- Dashboard: Living Orbit Workbench
- PR list: Signal Feed
- PR detail: Scan Chamber
- Settings: Control Room

## Theme — custom Night Garden

- deep blue-black canvas
- emerald/cyan living signal
- muted royal/violet and gold blooms in the background
- amber/red risk spectrum
- surfaces use depth, softened borders, and glow restraint
- no literal rockets, planets, emoji, fake browser chrome, or gimmicky space art

## Typography

- Display: Inter 800, tight, roman
- Body: Inter 400–600
- Mono: JetBrains Mono for system telemetry, IDs, durations, and small labels
- No italic headings

## Motion

- Breathing pulse only for real running states
- Orbit rotation only for intentional scan/poll affordances
- Reduced-motion fallback must keep animation short
- No bouncy easing, no celebration effects

## Component voice

- Buttons: pill/input-radius, solid accent for primary, atmospheric outline for secondary
- Cards: panels, chambers, fields, signals
- Running review: “scanning” with pulse
- Review recommendations:
  - approve = clear
  - request changes = mutate
  - comment = observe

## Non-goals

- Do not preserve the previous admin-card layout.
- Do not add fake sci-fi chrome.
- Do not invent product metrics.
- Do not add a motion dependency unless a later task specifically needs it.
