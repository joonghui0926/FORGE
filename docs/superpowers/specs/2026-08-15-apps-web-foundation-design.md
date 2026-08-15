# apps/web Foundation — Design Spec

**Date:** 2026-08-15
**Surface:** Customer Portal (`apps/web`)
**Sub-project:** 1 of N — Foundation

---

## 1. Context

FORGE has three product surfaces:

| App | Audience | Status |
|-----|----------|--------|
| `apps/web` | Customers — order datasets, track progress, download results | **This spec** |
| `apps/capture` | Terac participants — mobile capture tool | Deferred |
| `apps/ops` | FORGE operators + agents — pipeline control | Deferred |

The FastAPI backend (`services/api`) is live with working endpoints for orders and captures. This spec covers the first deployable slice of `apps/web`.

---

## 2. Scope

### In scope

- Next.js 14 App Router project scaffolding
- Tailwind v4 with all FORGE design tokens
- Auth.js v5: Google + GitHub + Resend magic link → FORGE JWT session
- Landing page
- Auth screens (sign-in, error)
- Customer portal shell: authenticated layout + NavBar
- Orders list page (live data from API)
- New order stepper (6 steps, calls `POST /orders`)
- Order detail page: Overview tab (live) + placeholder tabs

### Explicitly deferred

- Workspace tabs beyond Overview (Acquisition, Processing, Quality, Episodes, Dataset, Activity, Billing)
- Dataset explorer and episode detail
- Customer review and approval flow
- Delivery / download screens
- Org/team management, Settings, Notifications, Developer settings
- `apps/capture`, `apps/ops`

---

## 3. Stack

| Concern | Choice | Reason |
|---------|--------|--------|
| Framework | Next.js 14, App Router | Server components, layouts, streaming |
| Styling | Tailwind CSS v4 | `@theme` maps FORGE tokens directly to utilities |
| Auth | Auth.js v5 (NextAuth) | App Router native, Google + GitHub + Resend magic link, no paid dependency |
| Language | TypeScript strict | Matches rest of monorepo |
| Font | Inter via `next/font/google` | Handoff §4.1 |
| Package manager | pnpm (workspace member) | Existing monorepo setup |

---

## 4. File structure

```
apps/web/
├── package.json
├── next.config.ts
├── auth.ts                            # Auth.js v5 config
├── middleware.ts                      # Redirect /orders/* without session
├── app/
│   ├── globals.css                    # @theme FORGE tokens + Tailwind import
│   ├── layout.tsx                     # <html> bg-forge-canvas, Inter, metadata
│   ├── page.tsx                       # Landing
│   ├── auth/
│   │   ├── signin/page.tsx
│   │   └── error/page.tsx
│   ├── orders/
│   │   ├── layout.tsx                 # Authenticated portal layout (NavBar)
│   │   ├── page.tsx                   # Order list — server component
│   │   ├── new/
│   │   │   └── page.tsx               # New order stepper — client component
│   │   └── [orderId]/
│   │       └── page.tsx               # Order detail + workspace tabs
│   └── api/
│       ├── auth/[...nextauth]/route.ts
│       └── token/route.ts             # Returns FORGE JWT for client-side fetches
├── components/
│   ├── layout/
│   │   └── NavBar.tsx
│   ├── landing/
│   │   ├── Hero.tsx
│   │   └── ProcessSteps.tsx
│   ├── orders/
│   │   ├── OrderRow.tsx
│   │   ├── OrderStatusBadge.tsx
│   │   ├── NewOrderStepper.tsx
│   │   ├── steps/
│   │   │   ├── SkillStep.tsx
│   │   │   ├── RobotStep.tsx
│   │   │   ├── CoverageStep.tsx
│   │   │   ├── VolumeQualityStep.tsx
│   │   │   ├── RightsStep.tsx
│   │   │   └── ReviewStep.tsx
│   │   └── workspace/
│   │       ├── WorkspaceTabs.tsx
│   │       ├── OverviewTab.tsx
│   │       └── PlaceholderTab.tsx
│   └── ui/
│       ├── Button.tsx
│       ├── Field.tsx
│       └── StatusBadge.tsx
└── lib/
    ├── api.ts
    └── session.ts
```

---

## 5. Design tokens

`app/globals.css` declares all FORGE tokens inside Tailwind v4's `@theme` block. This generates utilities (`bg-forge-canvas`, `text-forge-primary`, `rounded-control`, etc.) with zero config file needed.

```css
@import "tailwindcss";

@theme {
  /* Canvas & primary */
  --color-forge-canvas:        #F8F5EB;
  --color-forge-primary:       #00ABC2;
  --color-forge-primary-hover: #0095AA;
  --color-forge-primary-active:#007F91;
  --color-forge-primary-ink:   #082F35;

  /* Ink */
  --color-forge-ink:           #152126;
  --color-forge-ink-muted:     #53636A;
  --color-forge-ink-subtle:    #718087;

  /* Surfaces */
  --color-forge-surface:       #FFFEF9;
  --color-forge-surface-soft:  #F1EFE6;
  --color-forge-surface-cyan:  #DDF6F8;

  /* Borders */
  --color-forge-border:        #D8D6CC;
  --color-forge-border-strong: #B9C0BF;
  --color-forge-focus:         #007F91;

  /* Semantic */
  --color-forge-success:       #177A52;
  --color-forge-success-soft:  #E1F3EA;
  --color-forge-warning:       #9A6512;
  --color-forge-warning-soft:  #FFF0CF;
  --color-forge-danger:        #B33A3A;
  --color-forge-danger-soft:   #FBE5E2;
  --color-forge-info:          #246B8A;
  --color-forge-info-soft:     #E1F1F7;

  /* Typography */
  --font-sans: Inter, "Pretendard Variable", Pretendard, system-ui, sans-serif;
  --font-mono: "JetBrains Mono", "SFMono-Regular", Consolas, monospace;

  /* Shape */
  --radius-control: 12px;
  --radius-surface: 16px;
  --radius-pill:    999px;

  /* Spacing (augments Tailwind defaults) */
  --spacing-1: 4px;  --spacing-2: 8px;   --spacing-3: 12px;
  --spacing-4: 16px; --spacing-5: 24px;  --spacing-6: 32px;
  --spacing-7: 48px; --spacing-8: 64px;  --spacing-9: 96px;
}
```

`packages/ui/tokens/tokens.css` mirrors this file (without the Tailwind import) so future shared components can use the same custom properties.

---

## 6. Auth architecture

### Flow

```
Sign-in (Google / GitHub / Magic Link)
  → Auth.js signIn() callback
      → look up tenant by OAuth email in dataset_orders tenants table
      → if not found: create tenant row (org onboarding stub)
  → Auth.js jwt() callback
      → mint FORGE JWT { sub: userId, tenant_id, exp: +1h }
        signed with AUTH_SECRET (same secret FastAPI uses)
      → store in encrypted session cookie
  → Auth.js session() callback
      → expose { forgeToken, tenantId } on the session object

Server component / Route Handler
  → getServerSession(authOptions)
  → lib/api.ts attaches forgeToken as Authorization: Bearer

Client component (capture upload, stepper)
  → fetch('/api/token') → { token }
  → attaches as Authorization: Bearer on direct fetch calls
```

### Config (`auth.ts`)

- Providers: Google, GitHub, Resend (magic link)
- Session strategy: `jwt`
- `jwt` callback mints the FORGE HS256 token
- `session` callback exposes `forgeToken` and `tenantId`
- `signIn` callback handles tenant lookup / creation

### Middleware (`middleware.ts`)

Protects `/orders/:path*` and `/api/token`. Redirects unauthenticated requests to `/auth/signin`.

### Env vars required

```
AUTH_SECRET=                   # shared with FastAPI AUTH_SECRET
AUTH_GOOGLE_ID=
AUTH_GOOGLE_SECRET=
AUTH_GITHUB_ID=
AUTH_GITHUB_SECRET=
AUTH_RESEND_KEY=               # for magic link emails
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 7. API client (`lib/api.ts`)

Thin typed wrapper. Server-side calls read the session directly; client-side calls receive the token as a parameter (from `/api/token`).

```typescript
// Server-side usage (server components, route handlers)
import { apiServer } from '@/lib/api'
const orders = await apiServer.get<OrderResponse[]>('/orders')

// Client-side usage (client components)
import { apiFetch } from '@/lib/api'
const result = await apiFetch('/captures/upload-url', token, { method: 'POST', body })
```

All API errors surface a typed `{ detail: string }` shape — never a raw FastAPI trace to the customer.

---

## 8. Pages

### 8.1 Landing (`/`)

Structure (no cards, no HR separators):

```
[NavBar: logo + "Sign in"]

[Hero]
  Large headline: "Human demonstrations in."
  Large headline: "Validated robot-ready datasets out."
  Subtext (≤56ch): one sentence on what FORGE delivers
  Primary CTA: "Define your robot task"  →  /auth/signin?callbackUrl=/orders/new

[Process]  (Section heading + generous vertical space)
  7 numbered steps — plain text list, spacing as separator
  Dataset Planning → Human Acquisition → Physical Data Compilation
  → Robot Retargeting → Physics Validation → Dataset Amplification → Delivery

[Footer]  minimal — links only
```

Constraints (handoff §8.1): no logo wall before value prop, no metric claims without evidence, one primary CTA only.

### 8.2 Sign-in (`/auth/signin`)

Three provider buttons (Google, GitHub, Email magic link) on `--forge-surface` background. Each button is a full-width secondary button. Email input uses `Field` component — label above, not as placeholder. No password field (magic link only for now).

### 8.3 Orders list (`/orders`)

Server component. Fetches `GET /orders` on the server with the session Bearer token.

```
[NavBar — "Orders" active]

Page title: "Your Orders"          [Primary button: "New order"]
One-sentence descriptor

[Table]
  Columns: Skill name | Status | Episodes ordered | Created
  Status cell: StatusBadge (icon + plain-language label)
  Row click → /orders/[orderId]
  Empty state: headline + subtext + "Place your first order" CTA
  Error state: cause + "Try again" — no raw API error
```

Plain-language status mapping (never raw enum to customer):

| DB state | Customer sees |
|----------|---------------|
| DRAFT | Awaiting payment |
| PAID | Planning your collection |
| PLANNING | Planning your collection |
| ACQUIRING | Collecting demonstrations |
| PRE_QC / PROCESSING / CONTACTING / RETARGETING / VALIDATING / RECOLLECTING / AMPLIFYING / BATCH_QC / PACKAGING | Processing — [stage description] |
| READY | Ready for review |
| CANCELLED | Cancelled |
| FAILED | Needs attention |

### 8.4 New order stepper (`/orders/new`)

Client component. Six steps, progress bar always visible. State is local React (`useState`). No data is saved until the final step.

| Step | Title (question form) | Key fields |
|------|----------------------|------------|
| 1 — Skill | What should the robot do? | Task name, success state, failure conditions, phases |
| 2 — Robot | Which robot and hand? | Robot ID, hand type, URDF/MJCF URI (help text: "contact us if you need help"), joint limits URI |
| 3 — Coverage | Which objects and viewpoints? | Object IDs (tag input), viewpoint bins (checkboxes), grasp variation |
| 4 — Volume & Quality | How many episodes and what quality bar? | Validated episode count, replay required toggle, penetration / F1 / acceptance thresholds |
| 5 — Rights | Who owns the data? | Rights profile (3 radio options with plain-language descriptions) |
| 6 — Review | Does this look right? | Summary of all steps, "Place order" primary button |

On submit (step 6): calls `POST /orders`. If `stripe_payment_link` is returned, redirects there. If null (Stripe not configured), shows the `order_id` and a "Payment setup in progress" message. Error: field-level where possible, page-level summary for network failures.

Each step follows handoff §7.2: label above input, 48px min control height, error shows cause + fix action, required/optional marked consistently, technical schema names (e.g. `r2://`) explained in help text.

### 8.5 Order detail (`/orders/[orderId]`)

Server component wrapping client `WorkspaceTabs`.

```
[NavBar]

[PageHeader]
  Skill name                          [secondary: "Download" (disabled until READY)]
  Plain-language status sentence
  Next action or "We're waiting on: [stage]"

[WorkspaceTabs]
  Overview (active) | Acquisition | Processing | Quality | Episodes | Dataset | Activity | Billing
```

**Overview tab** (handoff §8.3):

```
[Status narrative]
  Current stage in plain language
  What happens next
  Estimated completion (stage + last update — not fake progress %)

[Key metrics]  — 1–3 large numbers inline, not a card grid
  e.g.  42 demonstrations collected · 18 passed pre-QC · 6 validated episodes

[Latest decision / evidence]  — narrative + expandable detail

[Coverage summary]  — object × viewpoint matrix (not cards)

[Billing summary]  — order total, payment status (plain text)
```

**Placeholder tabs**: heading "Coming soon" + one sentence on what this tab will show. No blank white boxes.

---

## 9. UI components

### Button (`components/ui/Button.tsx`)

Three variants matching handoff §7.1:

| Variant | Appearance | Use |
|---------|-----------|-----|
| `primary` | `bg-forge-primary`, `text-forge-primary-ink`, 44–48px height | One per page/step |
| `secondary` | transparent + `border-forge-border`, dark ink | Supporting actions |
| `tertiary` | text action, no border | Low-emphasis |

No cyan on danger actions. Loading state shows spinner inside button, not a separate overlay.

### Field (`components/ui/Field.tsx`)

- Label always visible above input (never placeholder-only)
- Input min height 48px, text 16px (prevents mobile zoom)
- Help text 14px below input
- Error text 14px directly below field — shows cause and fix action
- Associates label + error with `htmlFor` / `aria-describedby`

### StatusBadge (`components/ui/StatusBadge.tsx`)

Icon + label + optional detail string. Never color-only. Maps DB enum to customer-readable label via the mapping table in §8.3.

### NavBar (`components/layout/NavBar.tsx`)

Three items: Orders | Datasets | Account. Active item: `text-forge-primary` + heavier weight. No boxes around nav items. Datasets and Account are present but link to placeholder routes in sub-project 1.

---

## 10. States every screen must handle

Per handoff §15 (UI Definition of Done), each page implements:

| State | Behavior |
|-------|----------|
| Loading | Skeleton with screen reader label (not blank flash) |
| Empty | Headline + subtext + primary action |
| Error (network) | Cause in plain language + "Try again" — no raw API detail |
| Error (auth) | Redirect to sign-in via middleware |
| Partial data | Render what's available, mark missing sections clearly |
| Mobile | Single column, full-width primary buttons, 44×44px touch targets |
| Keyboard | All actions reachable, focus ring never removed, dialog focus trap |

---

## 11. R2 CORS (required for capture upload in later sub-project)

Not in scope for sub-project 1, but the config file is added now so it's not forgotten:

```json
// infra/r2-cors.json
[{
  "AllowedOrigins": ["http://localhost:3000", "https://forge.app"],
  "AllowedMethods": ["PUT"],
  "AllowedHeaders": ["Content-Type"],
  "MaxAgeSeconds": 3000
}]
```

Applied with: `aws s3api put-bucket-cors --bucket forge-dev --cors-configuration file://infra/r2-cors.json --endpoint-url $R2_ENDPOINT`

---

## 12. Out-of-scope patterns (enforced by handoff §14 checklist)

The implementation must not contain:
- White rounded cards wrapping every section
- Nested cards
- `<hr>` between every section
- Heavy per-row borders
- Text below 14px
- `#00ABC2` fill with white small text (use `--forge-primary-ink` dark ink)
- Color-only status (always icon + label)
- Multiple primary buttons on one screen
- Raw API error strings shown to the customer (`FAILED`, `Error 0x...`)
- Fake progress percentages for GPU/async work (show stage + last update)
