# Design — PR Review Dashboard

A locked design system for this app. Every page redesign reads this file before
emitting code. Do not regenerate per page — extend or amend this file when the
system needs to grow.

## Genre
atmospheric

## Macrostructure family
- App pages: Workbench (sidebar + content area, functional density)
- No marketing or content pages in this app.

## Theme — Midnight

- `--color-paper`     oklch(13% 0.008 260)     deep blue-black
- `--color-paper-2`   oklch(16% 0.010 260)     raised surface
- `--color-paper-3`   oklch(19% 0.010 260)     elevated surface
- `--color-ink`       oklch(94% 0.006 260)     primary text
- `--color-ink-2`     oklch(72% 0.008 260)     secondary text
- `--color-ink-3`     oklch(52% 0.008 260)     muted text
- `--color-rule`      oklch(26% 0.010 260)     borders
- `--color-accent`    oklch(72% 0.17 160)      emerald
- `--color-accent-2`  oklch(65% 0.15 160)      emerald darker
- `--color-focus`     oklch(72% 0.17 160)      focus ring (same as accent)
- `--color-danger`    oklch(62% 0.22 25)       red
- `--color-warning`   oklch(75% 0.18 80)       amber
- `--color-info`      oklch(65% 0.15 250)      blue

## Typography
- Display: Inter, weight 600, style normal
- Body:    Inter, weight 400
- Mono:    JetBrains Mono, weight 400
- Display tracking: -0.025em
- Type scale anchor: major third (1.25) from 16px base

## Spacing
4-point named scale. The values are in `tokens.css`. Pages must use named
tokens (`var(--space-md)`), never raw values.

## Motion
- Easings: `--ease-out: cubic-bezier(0.16, 1, 0.3, 1)`
- Reveal pattern: fade + subtle slide (transform + opacity only)
- Reduced-motion fallback: opacity-only, ≤ 150ms

## Microinteractions stance
- Silent success (no celebratory toasts)
- Hover delay 800ms on tooltips · focus delay 0ms
- Button press: translateY(1px) on active
- Cards: subtle border-color shift on hover

## CTA voice
- Primary CTA: solid accent fill, 8px radius, 13px weight 600 text
- Secondary CTA: outline (rule border), 8px radius, 13px weight 500 text

## Per-page allowances
- App pages MUST NOT use enrichment — function carries the page.
- All pages share the sidebar nav, wordmark, accent colour, type pairing.
- Score rings use SVG + CSS animation (functional, not decorative).

## Exports

### tokens.css
See `src/tokens.css` for the complete token set.
