---
name: architecture-diagrams
description: Produce polished, presentation-ready SVG diagrams (plus a high-res PNG render) from design inputs — components, zones/groupings, flows, and step annotations. Use this skill whenever the user asks for an architecture diagram, system diagram, data-flow diagram, network topology, pipeline, integration map, hub-and-spoke visual, or any box-and-arrow figure for a document, TDD, design doc, slide, or README — even if they just say "draw this", "visualize the flow", or "we need a figure for this section". For Google Cloud / GCP architectures, this skill embeds the official GCP product icons. Do NOT use for charts of numeric data (bar/line/pie) or for editing photos.
---

# Architecture Diagrams

Turn a described design (components, groupings, flows, annotations) into a clean, publication-quality SVG diagram in a consistent house style, then render and visually verify a PNG.

The output must look like it came from a professional design system: aligned boxes, generous whitespace, a legend, and zero overlapping text. The single biggest quality lever is the **render-and-look loop** at the end — never deliver a diagram you haven't rendered and inspected with your own eyes.

## Workflow

### 1. Extract the design model first — before any SVG

From the user's input (conversation, doc, codebase), write down:

- **Components**: the boxes. Name + 1–3 short descriptor lines each.
- **Zones**: groupings that contain components (projects, VPCs, environments, org layers, "client side / server side"). Diagrams read best with 2–5 zones.
- **Flows**: arrows. Classify each as *request path* (solid), *response path* (dashed gray), or *data/logging/analytics* (dashed amber). Note which flows cross zone boundaries — those deserve labels.
- **Step annotations** (optional but powerful): if the source material describes a numbered sequence, assign step numbers to components/arrows and plan a step-key panel.

If key facts are missing (what talks to what, what's inside which boundary), ask — a wrong arrow in an architecture diagram is worse than no diagram.

### 2. Plan the layout on a coarse grid

- Primary flow runs **left → right** (or top → bottom for pipelines). Place the actor/client leftmost, analytics/storage in a bottom strip or rightmost.
- Sketch zone rectangles with explicit coordinates before writing components. Leave a **150–250px gap between zones** whose components exchange labeled arrows — cross-boundary labels live in that gap.
- Inside a zone: components on a row or 2×N grid, ≥40px apart, all inside the zone with ≥20px inset, below the zone's label line.
- Route arrows so they never pass through a box or a text label. Prefer straight horizontal/vertical; use one elbow when needed. If two boxes exchange request+response, draw two parallel lines offset ~40–60px vertically.
- Long explanations do not belong on arrows. Put a numbered badge on the arrow and the sentence in the step key.

### 3. Write the SVG

Read `references/style-spec.md` for the exact house style (canvas, palette, zone/box/badge/arrow/legend/step-key geometry) and start from `assets/template.svg`, which contains ready-made `<defs>` (arrow markers, drop shadow) and one canonical example of each element.

**GCP diagrams**: if any components are Google Cloud products (mentions of GCP, Google Cloud, BigQuery, GKE, Cloud Run, Pub/Sub, Vertex AI, and so on), also read `references/gcp-icons.md` and put the official GCP icon in each GCP component box. Practitioners recognize these icons faster than text, and their absence makes a GCP diagram look unofficial. Write `<!-- gcp-icon: name x y size -->` placeholder comments in the SVG and run `python scripts/gcp_icon.py --inject diagram.svg` to expand them — never write icon markup or base64 strings yourself; hand-transcribed data URIs corrupt silently and take the whole diagram down with them.

SVG text does not wrap — you must break lines manually. Estimate width as `chars × font-size × 0.52` (regular) or `× 0.62` (bold); letter-spacing adds `chars × spacing`. Keep every line ≤ box width − 2×padding. When a label won't fit, shorten the words rather than the font.

### 4. Inspect the SVG (mandatory)

```bash
python scripts/view.py diagram.svg
```

Then **open and actually look at the rendered diagram in the browser**. Check, in order:

1. Any text escaping its box, colliding with another label, or clipped at canvas edge?
2. Any arrow crossing through a box, a label, or a zone title?
3. Are parallel elements aligned (same y for boxes in a row, consistent gaps)?
4. Does the legend match the arrow styles actually used?
5. Do badge numbers on the canvas match the step key?
6. On GCP diagrams: does every GCP component box show its official icon, rendered (not a blank/black square), clear of the text block?

Fix and inspect again until all five pass. One or two fix cycles are normal; delivering without the visual check is the main way this skill fails.

### 5. Deliver

Produce the `.svg` file (source of truth, scalable, and easy to edit later). SVG is natively supported by modern browsers, Markdown previews, and documentation platforms, and can be embedded directly in documents.

## Sizing guidance

- Default canvas ~1920 wide. Height: ~700–900 for a simple diagram, 1100–1300 when a step key panel is included.
- **Match the chrome to the diagram's weight.** The legend, zones, and step key exist to make a *complex* diagram self-explanatory; on a small one they read as bureaucracy. For ≤5 components in an essentially linear flow (a pipeline, a simple chain — especially anything destined for a README): single row of boxes, small canvas (~1100×300), labels directly on the arrows, no zones, no legend, no step key, no numbered badges. Keep the house palette and box style so it still looks like family. Add each piece of chrome only when it pays rent: zones when there are real boundaries (trust, network, team, project), a step key when arrows need >4-word explanations, a legend when ≥2 arrow styles coexist.
- 6–10 components is the sweet spot for the full treatment. Over ~14, collapse repeated structures into one detailed instance plus dashed "same pattern" placeholders — repetition is the enemy of readability.
- Repeated/templated structures (N identical spokes, shards, regions): show **one in full detail**, then 1–2 collapsed dashed boxes labeled "same blueprint", plus an italic note that more can be added.

## Content principles

- Every box earns its place: name + what it does in ≤3 short lines. No paragraphs inside boxes.
- Security/trust boundaries are content, not decoration: when a flow crosses a boundary, label the mechanism (auth type, token, protocol) in the inter-zone gap.
- Use the user's real terminology (product names, project names, team names) — never generic placeholders like "Service A" unless the user's input is itself generic.
- The diagram should be self-explanatory to someone who has not read the surrounding document: that is what the legend and step key are for.
