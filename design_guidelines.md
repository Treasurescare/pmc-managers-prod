# PMC Managers — Design Guidelines v2.0 (Navy Trust)

Aesthetic identity: **Institutional gravitas × Enterprise procurement.** Think Bloomberg Terminal / FT / SAP Ariba, dialled 10x prettier.

## Brand assets
- Logo: `/app/frontend/public/pmc-logo.png` — letter P with globe motif and rising bar chart in navy. Never place on non-navy background at full-size; on light bg use the icon inside a 1px navy square.
- Hero image: `/app/frontend/public/hero-containers.jpg` — port at dusk. Use with `bg-gradient-to-r from-brand-navy via-brand-navy/40 to-transparent` overlay.

## Design tokens (source of truth: `tailwind.config.js` + `index.css`)
- `--brand-navy: #0f1b3d` (primary dark)
- `--brand-navy-deep: #1e3a5f`
- `--brand-navy-soft: #3b6fa0` (accent/CTA/link)
- `--brand-pale: #e8edf3` (page background)
- `--brand-surface: #ffffff` (cards/tables)
- Green LIVE pulse: `#22c55e` / `#4ade80` text

## Typography
- Display / headings: `font-display` → **Libre Baskerville**. Use italic for the accent phrase inside a sentence (e.g. "Procurement that *travels borders*.")
- Body / UI: `font-sans` → **IBM Plex Sans**
- Numbers / mono: `font-mono` → **IBM Plex Mono** with `font-variant-numeric: tabular-nums`
- Kickers/labels: `.pmc-label` — 11px, 600 weight, 0.2em tracking, uppercase, navy-soft color
- Big stat number: `.pmc-stat-lg` — 3rem Libre Baskerville 400 weight

## Component patterns
- **Corners**: everything is SHARP (radius 0). ONLY pills (`.pmc-pill` / `rounded-full`) are rounded.
- **Buttons**:
  - Primary: `bg-brand-navy-soft text-white shadow-brand-btn px-8 py-4 uppercase tracking-widest text-[0.8125rem] font-semibold hover:bg-brand-navy-soft/90`
  - Secondary (on navy): `bg-transparent border border-brand-navy-soft/50 text-white`
  - Dark: `bg-brand-navy text-white hover:bg-brand-navy-deep`
- **Cards**: `border border-brand-navy/10 bg-white p-8 hover:border-brand-navy-soft/40 transition-colors`
- **Pill**: `.pmc-pill` (light) / `.pmc-pill-navy` (dark). Use for kickers like "TENDER · TWO-ENVELOPE"
- **Data table**: `.pmc-table` — sticky header, dense (12px x 16px padding), tabular-nums, hover row = 4% navy tint
- **Dashboard sidebar**: 280px wide, `bg-brand-navy text-white`, active nav uses `border-l-2 border-brand-navy-soft bg-white/[0.06]`
- **Frosted glass live card**: `.pmc-glass` — `rgba(15,27,61,0.8)` + `backdrop-filter: blur(24px)` + `border rgba(255,255,255,0.1)`

## Motion (all under 300ms except pulse)
- Green LIVE dot pulse — 2s
- Live-card fade-up on landing — 0.7s
- Nav-item bg lift + left-border grow on hover
- Feature-card border → navy-soft on hover

## Layout rules
- Landing: asymmetric split (50/50 on lg+, stacked on sm). Never centered cards with equal spacing.
- Dashboards: `grid-cols-[280px_1fr_320px]` (sidebar / main / tender-feed rail). Rail collapses to 40px.
- Content sections use `.max-w-7xl mx-auto grid gap-12 lg:grid-cols-[4fr_8fr] lg:gap-16` — kicker+headline on left (4fr), content on right (8fr).

## Do not
- No purple/violet gradients on white
- No Inter/Roboto/system-ui — always IBM Plex Sans
- No centered equal-spacing card grids on the landing
- No rounded corners on cards/buttons/inputs/tables — only pills round
- No user-facing dark-mode toggle (sidebar is intrinsically dark; content is light)
- No emoji icons; always lucide-react
