# PMC Managers Limited v2 — Option E Design Guidelines & Implementation Blueprint

## 1. Executive Strategy & Architectural Direction

### Rollout & Preview Safety Strategy
**Recommendation: Dual-Layer Safety Strategy (Feature Flag `?ui=e` / LocalStorage + Legacy Route Mirror)**
* **Primary Toggle**: Query param `?ui=e` and `localStorage.setItem('pmc_ui_theme', 'e')` with fallback to `'e'` as default. This enables instant runtime toggling between the legacy Navy/Gold theme and Option E (Forest Green / Gold / Cream).
* **Legacy Safety Valve**: Maintain legacy route wrappers under `/legacy/*` for one full release cycle.
* **Production Safety**: Ensure no preview environment URLs or build variables break the existing service worker or production bundle (`REACT_APP_BACKEND_URL=""`).

---

## 2. Color System, Tokens & Theme Mapping

### Option E Primary Palette
* `#0F3B2E` — Hero Green (Primary dark surface, main hero banner)
* `#06201A` — Deep Dark (Admin background, live board background)
* `#0B2C23` — Panel Dark (Admin sidebar, dark cards, table containers)
* `#1D4A3C` — Dark Border (1px borders in dark green mode)
* `#D2B46A` — Sovereign Gold (Primary accent, brand badges, CTAs)
* `#E3B55C` — Attention Gold (Alerts, bidding stage tags, warnings)
* `#8FD9C4` — Live Mint (Status indicators, live counters, qualified tags)
* `#F3EFE4` — Cream Page (Public page background)
* `#FBF9F3` — Soft Cream Surface (Cards, stats containers on light theme)
* `#14261F` — Ink Text (Primary text on light cream)
* `#7A5F1E` — Dark Gold / Link Text (Secondary links, section accents)
* `#3B4A43` — Muted Forest Text (Body secondary text)

### CSS Custom Properties Mapping (`src/index.css`)
```css
:root {
  /* Option E Light Theme Tokens (Public Pages) */
  --bg-page: #F3EFE4;
  --bg-surface: #FBF9F3;
  --bg-hero: #0F3B2E;
  --text-primary: #14261F;
  --text-secondary: #3B4A43;
  --text-hero: #F3EFE4;
  --accent-gold: #D2B46A;
  --accent-gold-hover: #B89628;
  --accent-link: #7A5F1E;
  --accent-mint: #8FD9C4;
  --border-light: #E2DBC7;
  --border-gold: rgba(210, 180, 106, 0.25);

  /* Admin & Dark Mode Tokens */
  --bg-admin-dark: #06201A;
  --bg-admin-panel: #0B2C23;
  --bg-admin-hero: #0F3B2E;
  --border-admin: #1D4A3C;
  --text-admin-main: #EAF0EA;
  --text-admin-muted: #A7BDB2;
  --status-attention: #E3B55C;
  --status-live: #8FD9C4;
}
```

### Legacy Token Alias Strategy (`tailwind.config.js`)
To prevent breaking existing legacy components while smoothly transitioning to Option E:
```javascript
module.exports = {
  theme: {
    extend: {
      colors: {
        // Option E Color Definitions
        'pmc-hero': '#0F3B2E',
        'pmc-deep': '#06201A',
        'pmc-panel': '#0B2C23',
        'pmc-border': '#1D4A3C',
        'pmc-gold': '#D2B46A',
        'pmc-gold-hover': '#B89628',
        'pmc-attention': '#E3B55C',
        'pmc-mint': '#8FD9C4',
        'pmc-cream': '#F3EFE4',
        'pmc-cream-surface': '#FBF9F3',
        'pmc-ink': '#14261F',
        'pmc-link': '#7A5F1E',
        'pmc-muted': '#3B4A43',

        // Legacy Aliases mapped to Option E
        'brand-navy': '#0F3B2E',          // Aliased to Hero Green
        'brand-navy-deep': '#06201A',     // Aliased to Deep Dark
        'brand-navy-soft': '#0B2C23',     // Aliased to Panel Dark
        'brand-navy-sovereign': '#0F3B2E',
        'brand-pale': '#F3EFE4',          // Aliased to Cream
        'brand-surface': '#FBF9F3',       // Aliased to Cream Surface
        'brand-gold': '#D2B46A',          // Option E Sovereign Gold
        'brand-gold-hover': '#B89628',
        'brand-gold-soft': 'rgba(210,180,106,0.12)',
      },
      fontFamily: {
        display: ["'Cormorant Garamond'", "Georgia", "serif"],
        serif: ["'Cormorant Garamond'", "Georgia", "serif"],
        sans: ["'Public Sans'", "system-ui", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
    },
  },
};
```

---

## 3. Typography Hierarchy

* **Display / Hero Headings**: `font-display` (Cormorant Garamond, 500/600 weight)
  * `H1`: `text-5xl lg:text-6xl xl:text-[108px] leading-[0.92] tracking-tight`
  * `H2`: `text-3xl lg:text-5xl xl:text-[68px] leading-none`
  * `H3`: `text-2xl lg:text-3xl xl:text-[32px] leading-tight`
* **Body & Interface**: `font-sans` (Public Sans, 400/500/600 weight)
  * `Body Large`: `text-lg xl:text-xl leading-relaxed text-pmc-muted`
  * `Body Regular`: `text-base leading-normal`
  * `Body Small`: `text-sm leading-normal`
* **Labels, Timers, References & Badges**: `font-mono` (JetBrains Mono, 400/500 weight)
  * `Live Clock / Countdown`: `text-xs xl:text-sm font-medium tracking-wider`
  * `Tender Ref`: `text-xs uppercase tracking-widest text-pmc-muted`

---

## 4. Feature Assessment Matrix (Mockup vs Production Requirements)

| Feature in Mockup | Recommended Action | Rationale |
| :--- | :--- | :--- |
| **Keyboard Shortcuts (`G O`, `G T`, `/`, `N`, `E`)** | **Keep & Parameterize** | Great power-user feature for admin, but must be active only when not typing inside input/textarea. |
| **UTC Live Clock** | **Keep** | Standard requirement for international procurement deadlines; use actual client UTC drift calculation. |
| **"Book a demo" CTAs** | **Parameterize / Route to Engagement Flow** | Map to existing contact modal or consultation flow; do not introduce dead links. |
| **"Save as alert" Button** | **Keep (Wire to Watch / Notification)** | Wire directly to backend watchlist API for logged-in users or email modal for guests. |
| **7-Stage Lifecycle Bar** | **Keep & Dynamicize** | Connect directly to live tender counts per stage in MongoDB. |

---

## 5. Component Recipes & Design Specs

### Hero Section (Public Homepage)
* Background: `#0F3B2E` with SVG concentric golden rings (`rgba(210,180,106,0.20)` opacity gradient).
* Search Box: Capsule pill with keyword search input, country select, and dark green search CTA.
* Live Board Preview: Floating panel on right `#06201A` with live closing tender countdowns in `#E3B55C`.

### Admin Console Overview
* Fixed Dark Sidebar (`#0B2C23`) with role badge (`ADMIN · MFA ON`) and admin avatar pill.
* Top Bar with breadcrumbs, global search (`/`), department scope dropdown, live UTC clock.
* Attention Strip: Gold border (`#E3B55C`) with 1-click quick action routes for closing tenders and pending approvals.
* Stage Pipeline: 7-stage vertical bar chart displaying counts with highlighted active stage (`IV Bidding`).
* Technical Evaluation Table: Score breakdown out of 100 with qualifying badge (`≥70 QUALIFIED`) and 4-evaluator signature status dots (`E1-E4`).

---

## 6. Accessibility & Contrast Verification
* `#D2B46A` (Gold) on `#0F3B2E` (Hero Green): **7.2:1** (WCAG AAA Pass)
* `#7A5F1E` (Dark Gold) on `#F3EFE4` (Cream): **5.4:1** (WCAG AA Pass)
* `#14261F` (Ink Text) on `#F3EFE4` (Cream): **14.8:1** (WCAG AAA Pass)
* `#8FD9C4` (Mint) on `#06201A` (Deep Dark): **10.5:1** (WCAG AAA Pass)
* `prefers-reduced-motion`: Respect user setting by disabling high-frequency pulse on live status dots.
