# House Style Spec

Exact values for every element. Copy the `<defs>` from `assets/template.svg` rather than rewriting markers/filters.

## Canvas & typography

- `<svg viewBox="0 0 1920 H" xmlns="http://www.w3.org/2000/svg" font-family="Helvetica Neue, Helvetica, Arial, sans-serif">` with a full-canvas white `<rect>`.
- Title: 29px bold `#202124` at (40, 54). Subtitle: 15px `#5F6368` at (40, 84) — one line summarizing the flow with `→` separators.
- Text colors: titles/names `#202124`, descriptors `#5F6368`. Component names 15px bold; descriptor lines 12px, 17px line spacing; small annotations 11.5px (italic for asides).

## Palette (fixed)

| Role | Fill | Stroke/Accent | Label text |
|---|---|---|---|
| Neutral zone (actors/clients) | `#F8F9FA` | `#80868B` | `#5F6368` |
| Primary zone (core system) | `#EEF4FE` | `#4285F4` | `#1967D2` |
| Secondary zone (isolated/peer systems) | `#EDF7EF` | `#34A853` | `#188038` |
| Data/analytics zone | `#FEF9E7` | `#F9AB00` | `#B06000` |
| Security-critical component accent | — | `#EA4335` | — |
| Request arrows | `#1A73E8` | | |
| Response arrows | `#5F6368` | | |
| Logging/analytics arrows | `#E37400` (label `#B06000`) | | |
| Step badges | `#174EA6` fill, white bold text | | |

Assign zone colors by role, in this order of precedence. With >4 zones, reuse the neutral gray.

## Zones

- Rounded rect: `rx="16"`, fill from palette, `stroke-width="2"`, `stroke-dasharray="8 6"`.
- Label: UPPERCASE, 13px bold, `letter-spacing="1.5"`, zone label color, at (zone.x+24, zone.y+32). Pattern: `NAME — QUALIFIER` (e.g. `AGENCY SPOKES — ISOLATED GCP PROJECTS`).
- Keep zone labels short enough not to collide with arrows entering the zone top; if the zone has an arrow entering from above, move the label to the zone's bottom-left instead.

## Component boxes

- White rect, `rx="10"`, `stroke="#DADCE0"` 1.5, drop shadow `filter="url(#shadow)"`.
- Accent bar: 6px-wide rect on the left edge (`rx="3"`), colored by the zone's stroke color — or `#EA4335` for security components, `#F9AB00` for data stores/analytics.
- Padding: first text line baseline ≈ y+32; left inset 22px (28px if a corner badge overlaps).
- Highlighted component (the protagonist, e.g. the entry widget): stroke in zone accent color at width 2 instead of gray.
- Nested boxes (components inside a detailed parent box): `rx="8"`, 5px accent bar, name 12.5px bold, descriptor 11.5px.
- Collapsed/repeat placeholders: `fill-opacity="0.75"`, dashed stroke (`7 5`) in zone color, name + one "Same blueprint: …" line.

## Arrows

Markers from template: `aBlue`, `aGray`, `aAmber` (`orient="auto-start-reverse"` so `marker-start` works for double-headed lines).

- Request: `stroke="#1A73E8" stroke-width="2.5" marker-end="url(#aBlue)"`.
- Response: `stroke="#5F6368" stroke-width="2" stroke-dasharray="6 4" marker-end="url(#aGray)"`, routed parallel to its request arrow, offset 40–60px.
- Logging/analytics: `stroke="#E37400" stroke-width="2.5" stroke-dasharray="6 4" marker-end="url(#aAmber)"`.
- Bidirectional "streamed through" connector: gray 1.8, `marker-start` + `marker-end`.
- End arrows 4px before the target edge so the head touches, not overlaps.
- Arrow labels: 12px, ≤3 short lines, centered (`text-anchor="middle"`) in the inter-zone gap **above** the arrow; put response-arrow labels below. Bold the mechanism line (e.g. "token impersonation (OIDC)").

## Step badges

- On-canvas: `<circle r="14" fill="#174EA6">` + centered white bold 14px number (dy ≈ +5.5). Place on the arrow midpoint, or overlapping a box's top-left corner (circle centered exactly on the corner).
- In step key: `r="11"`, 12px number.
- Numbers must appear in reading order (left→right, top→bottom) and match the step key exactly.

## Legend (top-right)

White rect `rx="10"` stroke `#DADCE0`, ~600×78 at (1280, 26). Two rows: 40px sample line + 12.5px label for each arrow type used, plus a sample badge labeled "Step in §X" when steps are used. Only include rows for styles actually present.

## Step key panel (bottom)

- Full-width white rect `rx="14"` stroke `#DADCE0`, height ≈ 60 + 32×ceil(N/2).
- Header: `STEP KEY — <SOURCE>` in zone-label style, gray.
- Two columns (badge x=80 and x=975; text 22px right of badge), rows 32px apart.
- Row format: badge + `<text>` with a bold dark `<tspan>` lead phrase, then `— explanation` in gray 12.5px. One line each — tighten wording until it fits ~870px (≈105 chars).

## Text-width arithmetic (no auto-wrap in SVG)

`width ≈ chars × size × 0.52` (regular), `× 0.62` (bold), `+ chars × letter-spacing`. Examples: 28 chars at 12px ≈ 175px; a 46-char uppercase 13px label with 1.5 spacing ≈ 440px. Budget against (box width − 2×inset) and break lines yourself.

## Composition reminders

- Vertical rhythm inside boxes: name line(s), 6px gap, descriptor lines at 17–18px spacing.
- Inter-zone gap of 150–250px whenever a labeled arrow crosses between zones.
- Sub-flows within a detailed parent box get small arrows (16–20px long) between nested boxes.
- Italic footnotes (constraints, tenancy notes) go inside the relevant zone at 11.5px italic, zone label color or gray.
