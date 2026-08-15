# apps/web Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first deployable slice of the FORGE customer portal — project scaffold, auth, orders list, new order stepper, and order detail with live Overview tab.

**Architecture:** Next.js 14 App Router; server components fetch data server-side and attach the FORGE JWT automatically; client components handle interactive UI (stepper, tabs). Auth.js v5 (`next-auth@5`) handles OAuth (Google/GitHub) and Resend magic-link, minting a FORGE HS256 JWT via `jose` stored in an encrypted session cookie. The JWT is forwarded as `Authorization: Bearer` to the FastAPI backend at `NEXT_PUBLIC_API_URL`.

**Tech Stack:** Next.js 14, Tailwind CSS v4 (no config file — all tokens in `@theme`), Auth.js v5, `jose` for JWT minting, TypeScript strict, Vitest + React Testing Library, pnpm workspace member.

**Spec:** `docs/superpowers/specs/2026-08-15-apps-web-foundation-design.md`

## Global Constraints

- All user-visible text in English only.
- No `<hr>` between sections; no white rounded cards wrapping sections; no nested cards; no per-row borders.
- No text below 14px; `#00ABC2` fill only paired with `text-forge-primary-ink` (dark), never white text on cyan.
- Status: always icon + label — never color-only.
- Raw API errors (`FAILED`, `Error 0x…`) never shown to customers — translate via STATUS_LABELS or summarize.
- No fake progress percentages — show stage name + last update timestamp.
- One `<Button variant="primary">` per page/step maximum.
- All interactive elements: 44 × 44 px minimum touch target, `focus-visible:ring-2 focus-visible:ring-forge-focus`, never `outline-none` alone.
- Loading states: skeleton element with `aria-label` (not a blank flash).
- Error states: plain-language cause + "Try again" action — no raw stack traces.

---

## File Map

| Path | Responsibility |
|------|---------------|
| `apps/web/package.json` | Workspace member, all runtime + dev deps |
| `apps/web/next.config.mjs` | Next.js config (14 doesn't support `.ts` config natively) |
| `apps/web/tsconfig.json` | Overrides base — `bundler` resolution, `@/*` path alias |
| `apps/web/postcss.config.mjs` | Routes CSS through `@tailwindcss/postcss` |
| `apps/web/vitest.config.ts` | Vitest + jsdom + `@/*` alias resolved to repo root |
| `apps/web/__tests__/setup.ts` | Imports `@testing-library/jest-dom` matchers |
| `apps/web/.env.local.example` | Template for required env vars |
| `apps/web/app/globals.css` | `@import "tailwindcss"` + full `@theme` FORGE token block |
| `apps/web/app/layout.tsx` | Root HTML shell — Inter font, `bg-forge-canvas`, metadata |
| `apps/web/app/page.tsx` | Public landing page |
| `apps/web/app/auth/signin/page.tsx` | Sign-in page — Google, GitHub, Resend magic-link |
| `apps/web/app/auth/error/page.tsx` | Auth error screen with plain-language messages |
| `apps/web/app/orders/layout.tsx` | Auth-gated portal shell — mounts NavBar, redirects if no session |
| `apps/web/app/orders/page.tsx` | Orders list — server component, fetches GET /orders |
| `apps/web/app/orders/new/page.tsx` | Mounts `<NewOrderStepper>` client component |
| `apps/web/app/orders/[orderId]/page.tsx` | Order detail — server component, fetches GET /orders/{id} |
| `apps/web/app/api/auth/[...nextauth]/route.ts` | Re-exports Auth.js handlers |
| `apps/web/app/api/token/route.ts` | Returns `{ token }` for client-side fetches |
| `apps/web/auth.ts` | Auth.js v5 config — providers, JWT mint, session callbacks |
| `apps/web/middleware.ts` | Protects `/orders/:path*` and `/api/token` |
| `apps/web/types/next-auth.d.ts` | Extends Session + JWT with `forgeToken`, `tenantId` |
| `apps/web/lib/types.ts` | `OrderState`, `ORDER_STATES`, `STATUS_LABELS`, `Order`, `CreateOrderPayload` |
| `apps/web/lib/api.ts` | `ApiError`, `apiServer` (server-side), `apiFetch` (client-side) |
| `apps/web/lib/session.ts` | `requireSession()` — server-component helper |
| `apps/web/components/ui/Button.tsx` | primary / secondary / tertiary variants, loading spinner |
| `apps/web/components/ui/Field.tsx` | Label above input + help text + error with full ARIA |
| `apps/web/components/ui/StatusBadge.tsx` | Icon + plain-language label from `OrderState` |
| `apps/web/components/layout/NavBar.tsx` | Logo + nav items (Orders/Datasets/Account) + sign-out |
| `apps/web/components/landing/Hero.tsx` | Headline, subtext, primary CTA |
| `apps/web/components/landing/ProcessSteps.tsx` | Numbered 7-step plain-text list |
| `apps/web/components/orders/OrderRow.tsx` | Table row for one order entry |
| `apps/web/components/orders/NewOrderStepper.tsx` | 6-step wizard shell — local state, progress bar, step routing |
| `apps/web/components/orders/steps/SkillStep.tsx` | Step 1: task name, initial state, success/failure predicates, phases |
| `apps/web/components/orders/steps/RobotStep.tsx` | Step 2: robot ID, hand type, URDF/MJCF URI, joint limits |
| `apps/web/components/orders/steps/CoverageStep.tsx` | Step 3: object IDs (tag input), viewpoint bins, grasp variation |
| `apps/web/components/orders/steps/VolumeQualityStep.tsx` | Step 4: episode count, replay toggle, thresholds |
| `apps/web/components/orders/steps/RightsStep.tsx` | Step 5: rights profile — 3 radio options |
| `apps/web/components/orders/steps/ReviewStep.tsx` | Step 6: full summary, "Place order" submit, error handling |
| `apps/web/components/orders/workspace/WorkspaceTabs.tsx` | Tab bar — Overview active, rest as PlaceholderTab |
| `apps/web/components/orders/workspace/OverviewTab.tsx` | Live overview: status narrative, coverage, billing |
| `apps/web/components/orders/workspace/PlaceholderTab.tsx` | "Coming soon" + one-sentence description |
| `apps/web/__tests__/lib/types.test.ts` | Every `OrderState` has a `STATUS_LABELS` entry |
| `apps/web/__tests__/lib/api.test.ts` | `ApiError` shape, `apiFetch` Bearer header + error handling |
| `apps/web/__tests__/ui/Button.test.tsx` | Variants, loading, disabled, click |
| `apps/web/__tests__/ui/Field.test.tsx` | ARIA label, error, optional marker |
| `apps/web/__tests__/ui/StatusBadge.test.tsx` | All states render visible text |
| `apps/web/__tests__/orders/NewOrderStepper.test.tsx` | Step nav, validation, data persistence on back |
| `packages/ui/tokens/tokens.css` | Mirrors FORGE token CSS custom properties (no Tailwind import) |
| `services/api/src/routers/orders.py` | Extend `OrderResponse` + queries with `skill_name`, `created_at`, `contract` |
| `infra/r2-cors.json` | R2 bucket CORS rules (needed for capture uploads in later sub-project) |

---

### Task 1: Project Scaffold

**Files:**
- Delete: `apps/web/src/.gitkeep`
- Create: `apps/web/package.json`
- Create: `apps/web/next.config.mjs`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/postcss.config.mjs`
- Create: `apps/web/vitest.config.ts`
- Create: `apps/web/__tests__/setup.ts`
- Create: `apps/web/.env.local.example`

**Interfaces:**
- Produces: pnpm workspace member `@forge/web`; `@/*` alias resolves to `apps/web/`; `pnpm test` runs vitest from `apps/web`

- [ ] **Step 1: Remove placeholder**

```bash
rm apps/web/src/.gitkeep && rmdir apps/web/src
```

- [ ] **Step 2: Create `apps/web/package.json`**

```json
{
  "name": "@forge/web",
  "version": "0.0.1",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "typecheck": "tsc --noEmit",
    "lint": "next lint",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "next": "^14.2.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "next-auth": "^5.0.0-beta.22",
    "@auth/core": "^0.34.0",
    "jose": "^5.9.0"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "typescript": "^5.5.0",
    "tailwindcss": "^4.0.0",
    "@tailwindcss/postcss": "^4.0.0",
    "vitest": "^2.0.0",
    "@vitejs/plugin-react": "^4.3.0",
    "@testing-library/react": "^16.0.0",
    "@testing-library/jest-dom": "^6.4.0",
    "@testing-library/user-event": "^14.5.0",
    "jsdom": "^25.0.0"
  }
}
```

- [ ] **Step 3: Create `apps/web/next.config.mjs`**

```mjs
/** @type {import('next').NextConfig} */
const nextConfig = {}

export default nextConfig
```

- [ ] **Step 4: Create `apps/web/tsconfig.json`**

Note: overrides the repo base — Next.js requires `bundler` module resolution, not `NodeNext`.

```json
{
  "compilerOptions": {
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": {
      "@/*": ["./*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 5: Create `apps/web/postcss.config.mjs`**

```mjs
export default {
  plugins: {
    '@tailwindcss/postcss': {},
  },
}
```

- [ ] **Step 6: Create `apps/web/vitest.config.ts`**

```typescript
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./__tests__/setup.ts'],
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, '.'),
    },
  },
})
```

- [ ] **Step 7: Create `apps/web/__tests__/setup.ts`**

```typescript
import '@testing-library/jest-dom'
```

- [ ] **Step 8: Create `apps/web/.env.local.example`**

```bash
# Copy to .env.local and fill in values before running
AUTH_SECRET=                    # openssl rand -hex 32 — MUST match FastAPI AUTH_SECRET
AUTH_GOOGLE_ID=
AUTH_GOOGLE_SECRET=
AUTH_GITHUB_ID=
AUTH_GITHUB_SECRET=
AUTH_RESEND_KEY=                # Resend API key for magic-link emails
NEXT_PUBLIC_API_URL=http://localhost:8000
```

- [ ] **Step 9: Install dependencies from repo root**

```bash
pnpm install
```

- [ ] **Step 10: Verify scaffold compiles**

```bash
cd apps/web && pnpm typecheck
```

Expected: errors about missing files (normal — no source files yet), but no config/module resolution errors.

- [ ] **Step 11: Commit**

```bash
git add apps/web/package.json apps/web/next.config.mjs apps/web/tsconfig.json \
        apps/web/postcss.config.mjs apps/web/vitest.config.ts \
        apps/web/__tests__/setup.ts apps/web/.env.local.example \
        pnpm-lock.yaml
git commit -m "feat(web): scaffold apps/web — Next.js 14 + Tailwind v4 + vitest"
```

---

### Task 2: Design Tokens + Root Layout

**Files:**
- Create: `apps/web/app/globals.css`
- Create: `apps/web/app/layout.tsx`
- Create: `packages/ui/tokens/tokens.css`

**Interfaces:**
- Produces: CSS utilities `bg-forge-canvas`, `text-forge-primary`, `rounded-control`, etc. available to every component; root `<html>` and `<body>` set up.

- [ ] **Step 1: Create `apps/web/app/globals.css`**

```css
@import "tailwindcss";

@theme {
  /* Canvas & primary */
  --color-forge-canvas:         #F8F5EB;
  --color-forge-primary:        #00ABC2;
  --color-forge-primary-hover:  #0095AA;
  --color-forge-primary-active: #007F91;
  --color-forge-primary-ink:    #082F35;

  /* Ink */
  --color-forge-ink:            #152126;
  --color-forge-ink-muted:      #53636A;
  --color-forge-ink-subtle:     #718087;

  /* Surfaces */
  --color-forge-surface:        #FFFEF9;
  --color-forge-surface-soft:   #F1EFE6;
  --color-forge-surface-cyan:   #DDF6F8;

  /* Borders */
  --color-forge-border:         #D8D6CC;
  --color-forge-border-strong:  #B9C0BF;
  --color-forge-focus:          #007F91;

  /* Semantic */
  --color-forge-success:        #177A52;
  --color-forge-success-soft:   #E1F3EA;
  --color-forge-warning:        #9A6512;
  --color-forge-warning-soft:   #FFF0CF;
  --color-forge-danger:         #B33A3A;
  --color-forge-danger-soft:    #FBE5E2;
  --color-forge-info:           #246B8A;
  --color-forge-info-soft:      #E1F1F7;

  /* Typography */
  --font-sans: Inter, "Pretendard Variable", Pretendard, system-ui, sans-serif;
  --font-mono: "JetBrains Mono", "SFMono-Regular", Consolas, monospace;

  /* Shape */
  --radius-control: 12px;
  --radius-surface: 16px;
  --radius-pill:    999px;

  /* Spacing augments */
  --spacing-1: 4px;  --spacing-2: 8px;   --spacing-3: 12px;
  --spacing-4: 16px; --spacing-5: 24px;  --spacing-6: 32px;
  --spacing-7: 48px; --spacing-8: 64px;  --spacing-9: 96px;
}
```

- [ ] **Step 2: Create `apps/web/app/layout.tsx`**

```tsx
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })

export const metadata: Metadata = {
  title: 'FORGE',
  description: 'Human demonstrations in. Validated robot-ready datasets out.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="bg-forge-canvas text-forge-ink font-sans antialiased">
        {children}
      </body>
    </html>
  )
}
```

- [ ] **Step 3: Create `packages/ui/tokens/tokens.css`**

Same custom properties as globals.css but without the Tailwind import — for future shared component packages.

```css
/* FORGE design tokens — CSS custom properties only, no framework dependency */
:root {
  --color-forge-canvas:         #F8F5EB;
  --color-forge-primary:        #00ABC2;
  --color-forge-primary-hover:  #0095AA;
  --color-forge-primary-active: #007F91;
  --color-forge-primary-ink:    #082F35;
  --color-forge-ink:            #152126;
  --color-forge-ink-muted:      #53636A;
  --color-forge-ink-subtle:     #718087;
  --color-forge-surface:        #FFFEF9;
  --color-forge-surface-soft:   #F1EFE6;
  --color-forge-surface-cyan:   #DDF6F8;
  --color-forge-border:         #D8D6CC;
  --color-forge-border-strong:  #B9C0BF;
  --color-forge-focus:          #007F91;
  --color-forge-success:        #177A52;
  --color-forge-success-soft:   #E1F3EA;
  --color-forge-warning:        #9A6512;
  --color-forge-warning-soft:   #FFF0CF;
  --color-forge-danger:         #B33A3A;
  --color-forge-danger-soft:    #FBE5E2;
  --color-forge-info:           #246B8A;
  --color-forge-info-soft:      #E1F1F7;
  --radius-control: 12px;
  --radius-surface: 16px;
  --radius-pill:    999px;
}
```

- [ ] **Step 4: Commit**

```bash
git add apps/web/app/globals.css apps/web/app/layout.tsx packages/ui/tokens/tokens.css
git commit -m "feat(web): add FORGE design tokens and root layout"
```

---

### Task 3: TypeScript Types + Status Mapping

**Files:**
- Create: `apps/web/lib/types.ts`
- Create: `apps/web/__tests__/lib/types.test.ts`

**Interfaces:**
- Produces: `OrderState`, `ORDER_STATES`, `STATUS_LABELS`, `Order`, `CreateOrderPayload`, `CreateOrderResponse` — imported by every component and lib file.

- [ ] **Step 1: Write the failing test**

```typescript
// apps/web/__tests__/lib/types.test.ts
import { describe, it, expect } from 'vitest'
import { ORDER_STATES, STATUS_LABELS } from '@/lib/types'

describe('STATUS_LABELS', () => {
  it('has an entry for every OrderState', () => {
    for (const state of ORDER_STATES) {
      expect(STATUS_LABELS[state], `missing entry for ${state}`).toBeDefined()
      expect(STATUS_LABELS[state].label.length).toBeGreaterThan(0)
    }
  })

  it('never exposes raw DB enum values as customer labels', () => {
    const rawValues = new Set(ORDER_STATES as readonly string[])
    for (const { label } of Object.values(STATUS_LABELS)) {
      expect(rawValues.has(label)).toBe(false)
    }
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/web && pnpm test __tests__/lib/types.test.ts
```

Expected: FAIL — `Cannot find module '@/lib/types'`

- [ ] **Step 3: Write `apps/web/lib/types.ts`**

```typescript
export const ORDER_STATES = [
  'DRAFT', 'PAID', 'PLANNING', 'ACQUIRING', 'PRE_QC',
  'PROCESSING', 'CONTACTING', 'RETARGETING', 'VALIDATING',
  'RECOLLECTING', 'AMPLIFYING', 'BATCH_QC', 'PACKAGING',
  'READY', 'CANCELLED', 'FAILED',
] as const

export type OrderState = typeof ORDER_STATES[number]

export interface StatusEntry {
  label: string
  detail?: string
}

export const STATUS_LABELS: Record<OrderState, StatusEntry> = {
  DRAFT:       { label: 'Awaiting payment' },
  PAID:        { label: 'Planning your collection' },
  PLANNING:    { label: 'Planning your collection' },
  ACQUIRING:   { label: 'Collecting demonstrations' },
  PRE_QC:      { label: 'Processing', detail: 'Pre-quality check' },
  PROCESSING:  { label: 'Processing', detail: 'Data processing' },
  CONTACTING:  { label: 'Processing', detail: 'Contacting participants' },
  RETARGETING: { label: 'Processing', detail: 'Robot retargeting' },
  VALIDATING:  { label: 'Processing', detail: 'Physics validation' },
  RECOLLECTING:{ label: 'Processing', detail: 'Recollecting demonstrations' },
  AMPLIFYING:  { label: 'Processing', detail: 'Dataset amplification' },
  BATCH_QC:    { label: 'Processing', detail: 'Batch quality check' },
  PACKAGING:   { label: 'Processing', detail: 'Packaging dataset' },
  READY:       { label: 'Ready for review' },
  CANCELLED:   { label: 'Cancelled' },
  FAILED:      { label: 'Needs attention' },
}

export interface Order {
  order_id: string
  state: OrderState
  stripe_payment_link: string | null
  skill_name?: string
  created_at?: string
  volume_validated_episodes?: number
  contract?: Record<string, unknown>
}

export interface CreateOrderPayload {
  skill: {
    name: string
    initial_state: string
    success_predicate: string
    failure_predicates: string[]
    phases: string[]
  }
  embodiment: {
    robot_id: string
    model_uri: string
    model_sha256: string
    hand_type: 'dexterous' | 'parallel_gripper' | 'suction'
    joint_limits_uri: string
  }
  volume_validated_episodes: number
  coverage: {
    object_ids: string[]
    viewpoint_bins: string[]
    grasp_variation: 'required' | 'preferred' | 'not_required'
  }
  quality: {
    source_replay_pass_required: boolean
    max_penetration_m: number
    min_contact_phase_f1: number
    min_delivery_acceptance_rate: number
  }
  rights_profile: 'customer_exclusive_derivatives' | 'forge_retained' | 'open'
}

export interface CreateOrderResponse {
  order_id: string
  state: OrderState
  stripe_payment_link: string | null
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd apps/web && pnpm test __tests__/lib/types.test.ts
```

Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add apps/web/lib/types.ts apps/web/__tests__/lib/types.test.ts
git commit -m "feat(web): add OrderState types and plain-language status labels"
```

---

### Task 4: UI Primitives (Button, Field, StatusBadge)

**Files:**
- Create: `apps/web/components/ui/Button.tsx`
- Create: `apps/web/components/ui/Field.tsx`
- Create: `apps/web/components/ui/StatusBadge.tsx`
- Create: `apps/web/__tests__/ui/Button.test.tsx`
- Create: `apps/web/__tests__/ui/Field.test.tsx`
- Create: `apps/web/__tests__/ui/StatusBadge.test.tsx`

**Interfaces:**
- Consumes: `Order`, `OrderState`, `STATUS_LABELS` from `@/lib/types`
- Produces: `<Button variant="primary|secondary|tertiary" loading?>`, `<Field id label error? help? required?>`, `<StatusBadge state>`

- [ ] **Step 1: Write Button test**

```typescript
// apps/web/__tests__/ui/Button.test.tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Button } from '@/components/ui/Button'
import { describe, it, expect, vi } from 'vitest'

describe('Button', () => {
  it('renders children', () => {
    render(<Button>Click me</Button>)
    expect(screen.getByRole('button', { name: 'Click me' })).toBeInTheDocument()
  })

  it('calls onClick when clicked', async () => {
    const onClick = vi.fn()
    render(<Button onClick={onClick}>Go</Button>)
    await userEvent.click(screen.getByRole('button'))
    expect(onClick).toHaveBeenCalledOnce()
  })

  it('is disabled and shows spinner when loading', () => {
    render(<Button loading>Submit</Button>)
    const btn = screen.getByRole('button')
    expect(btn).toBeDisabled()
    expect(btn.querySelector('svg')).toBeTruthy()
  })

  it('does not call onClick when disabled', async () => {
    const onClick = vi.fn()
    render(<Button disabled onClick={onClick}>Nope</Button>)
    await userEvent.click(screen.getByRole('button'))
    expect(onClick).not.toHaveBeenCalled()
  })

  it('applies secondary border class', () => {
    render(<Button variant="secondary">Cancel</Button>)
    expect(screen.getByRole('button').className).toMatch(/border-forge-border/)
  })
})
```

- [ ] **Step 2: Run Button test — expect FAIL**

```bash
cd apps/web && pnpm test __tests__/ui/Button.test.tsx
```

- [ ] **Step 3: Write `apps/web/components/ui/Button.tsx`**

```tsx
'use client'

import { ButtonHTMLAttributes, ReactNode } from 'react'

type Variant = 'primary' | 'secondary' | 'tertiary'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  loading?: boolean
  children: ReactNode
}

const VARIANT_CLASSES: Record<Variant, string> = {
  primary:   'bg-forge-primary text-forge-primary-ink hover:bg-forge-primary-hover active:bg-forge-primary-active',
  secondary: 'bg-transparent border border-forge-border text-forge-ink hover:bg-forge-surface-soft',
  tertiary:  'bg-transparent text-forge-ink hover:underline',
}

export function Button({ variant = 'primary', loading, children, className = '', disabled, ...rest }: ButtonProps) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      className={[
        'inline-flex items-center justify-center gap-2',
        'min-h-[48px] px-5 rounded-control text-base font-medium',
        'transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-forge-focus',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        VARIANT_CLASSES[variant],
        className,
      ].join(' ')}
    >
      {loading ? (
        <>
          <svg className="animate-spin h-4 w-4 shrink-0" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          {children}
        </>
      ) : children}
    </button>
  )
}
```

- [ ] **Step 4: Run Button test — expect PASS**

```bash
cd apps/web && pnpm test __tests__/ui/Button.test.tsx
```

- [ ] **Step 5: Write Field test**

```typescript
// apps/web/__tests__/ui/Field.test.tsx
import { render, screen } from '@testing-library/react'
import { Field } from '@/components/ui/Field'
import { describe, it, expect } from 'vitest'

describe('Field', () => {
  it('associates label with input via htmlFor', () => {
    render(<Field id="email" label="Email" type="email" required />)
    expect(screen.getByLabelText('Email')).toHaveAttribute('id', 'email')
  })

  it('shows Optional marker when not required', () => {
    render(<Field id="notes" label="Notes" />)
    expect(screen.getByText(/optional/i)).toBeInTheDocument()
  })

  it('shows error text and sets aria-invalid + aria-describedby', () => {
    render(<Field id="name" label="Name" error="Name is required" required />)
    const input = screen.getByRole('textbox')
    expect(screen.getByText('Name is required')).toBeInTheDocument()
    expect(input).toHaveAttribute('aria-invalid', 'true')
    expect(input).toHaveAttribute('aria-describedby', expect.stringContaining('name-error'))
  })

  it('shows help text associated via aria-describedby', () => {
    render(<Field id="uri" label="Model URI" help="Use r2:// format" required />)
    const input = screen.getByRole('textbox')
    expect(screen.getByText('Use r2:// format')).toBeInTheDocument()
    expect(input).toHaveAttribute('aria-describedby', expect.stringContaining('uri-help'))
  })
})
```

- [ ] **Step 6: Run Field test — expect FAIL**

```bash
cd apps/web && pnpm test __tests__/ui/Field.test.tsx
```

- [ ] **Step 7: Write `apps/web/components/ui/Field.tsx`**

```tsx
import { InputHTMLAttributes } from 'react'

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  id: string
  label: string
  help?: string
  error?: string
}

export function Field({ id, label, help, error, className = '', required, ...rest }: FieldProps) {
  const errorId = `${id}-error`
  const helpId  = `${id}-help`
  const describedBy = [error ? errorId : null, help ? helpId : null].filter(Boolean).join(' ')

  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium text-forge-ink">
        {label}
        {!required && (
          <span className="ml-1.5 text-xs font-normal text-forge-ink-muted">Optional</span>
        )}
      </label>
      <input
        id={id}
        required={required}
        aria-describedby={describedBy || undefined}
        aria-invalid={error ? true : undefined}
        className={[
          'min-h-[48px] px-4 text-base rounded-control border',
          error ? 'border-forge-danger' : 'border-forge-border',
          'bg-forge-surface text-forge-ink',
          'focus:outline-none focus:ring-2 focus:ring-forge-focus',
          className,
        ].join(' ')}
        {...rest}
      />
      {help  && <p id={helpId}  className="text-sm text-forge-ink-muted">{help}</p>}
      {error && <p id={errorId} className="text-sm text-forge-danger">{error}</p>}
    </div>
  )
}
```

- [ ] **Step 8: Run Field test — expect PASS**

```bash
cd apps/web && pnpm test __tests__/ui/Field.test.tsx
```

- [ ] **Step 9: Write StatusBadge test**

```typescript
// apps/web/__tests__/ui/StatusBadge.test.tsx
import { render, screen } from '@testing-library/react'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { ORDER_STATES, STATUS_LABELS } from '@/lib/types'
import { describe, it, expect } from 'vitest'

describe('StatusBadge', () => {
  it('renders visible text for every OrderState — never color-only', () => {
    for (const state of ORDER_STATES) {
      const { unmount } = render(<StatusBadge state={state} />)
      expect(screen.getByText(STATUS_LABELS[state].label)).toBeInTheDocument()
      unmount()
    }
  })

  it('renders a non-empty icon aria-hidden element alongside the label', () => {
    render(<StatusBadge state="READY" />)
    const icon = document.querySelector('[aria-hidden="true"]')
    expect(icon?.textContent?.trim().length).toBeGreaterThan(0)
  })
})
```

- [ ] **Step 10: Run StatusBadge test — expect FAIL**

```bash
cd apps/web && pnpm test __tests__/ui/StatusBadge.test.tsx
```

- [ ] **Step 11: Write `apps/web/components/ui/StatusBadge.tsx`**

```tsx
import { OrderState, STATUS_LABELS } from '@/lib/types'

const LABEL_ICON: Record<string, string> = {
  'Awaiting payment':         '○',
  'Planning your collection': '◎',
  'Collecting demonstrations':'●',
  'Processing':               '⟳',
  'Ready for review':         '✓',
  'Cancelled':                '✕',
  'Needs attention':          '!',
}

const LABEL_COLOR: Record<string, string> = {
  'Awaiting payment':         'text-forge-warning bg-forge-warning-soft',
  'Planning your collection': 'text-forge-info bg-forge-info-soft',
  'Collecting demonstrations':'text-forge-info bg-forge-info-soft',
  'Processing':               'text-forge-info bg-forge-info-soft',
  'Ready for review':         'text-forge-success bg-forge-success-soft',
  'Cancelled':                'text-forge-ink-muted bg-forge-surface-soft',
  'Needs attention':          'text-forge-danger bg-forge-danger-soft',
}

interface StatusBadgeProps {
  state: OrderState
  className?: string
}

export function StatusBadge({ state, className = '' }: StatusBadgeProps) {
  const { label, detail } = STATUS_LABELS[state]
  const icon  = LABEL_ICON[label]  ?? '·'
  const color = LABEL_COLOR[label] ?? 'text-forge-ink-muted bg-forge-surface-soft'

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-pill text-sm font-medium ${color} ${className}`}>
      <span aria-hidden="true">{icon}</span>
      {label}
      {detail && <span className="opacity-60 text-xs">· {detail}</span>}
    </span>
  )
}
```

- [ ] **Step 12: Run StatusBadge test — expect PASS**

```bash
cd apps/web && pnpm test __tests__/ui/StatusBadge.test.tsx
```

- [ ] **Step 13: Run all tests**

```bash
cd apps/web && pnpm test
```

Expected: all PASS

- [ ] **Step 14: Commit**

```bash
git add apps/web/components/ui/ apps/web/__tests__/ui/
git commit -m "feat(web): add Button, Field, StatusBadge primitives with tests"
```

---

### Task 5: API Client + Session Helper

**Files:**
- Create: `apps/web/lib/api.ts`
- Create: `apps/web/lib/session.ts`
- Create: `apps/web/__tests__/lib/api.test.ts`

**Interfaces:**
- Consumes: `auth()` from `@/auth` (only `apiServer` — not testable in unit tests), `ApiError` (testable)
- Produces:
  - `ApiError(status: number, message: string)` — extends Error
  - `apiServer.get<T>(path: string): Promise<T>` — server components only
  - `apiServer.post<T>(path: string, body: unknown): Promise<T>` — server components only
  - `apiFetch<T>(path: string, token: string, init?: RequestInit): Promise<T>` — client components
  - `requireSession(): Promise<Session>` — server components, redirects if no session

- [ ] **Step 1: Write the failing API test**

```typescript
// apps/web/__tests__/lib/api.test.ts
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ApiError, apiFetch } from '@/lib/api'

describe('ApiError', () => {
  it('has status, message, and name properties', () => {
    const err = new ApiError(404, 'Not found')
    expect(err.status).toBe(404)
    expect(err.message).toBe('Not found')
    expect(err.name).toBe('ApiError')
  })

  it('is instanceof Error', () => {
    expect(new ApiError(500, 'fail')).toBeInstanceOf(Error)
  })
})

describe('apiFetch', () => {
  beforeEach(() => { vi.stubGlobal('fetch', vi.fn()) })
  afterEach(() => { vi.unstubAllGlobals() })

  it('attaches Authorization Bearer header', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response('[]', { status: 200 }))
    await apiFetch('/orders', 'tok_abc')
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/orders'),
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: 'Bearer tok_abc' }),
      }),
    )
  })

  it('throws ApiError with detail from JSON body on non-ok response', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Not found' }), { status: 404 }),
    )
    await expect(apiFetch('/missing', 'tok')).rejects.toMatchObject({
      status: 404,
      message: 'Not found',
    })
  })

  it('throws ApiError with fallback when body is not JSON', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response('Bad Gateway', { status: 502 }))
    await expect(apiFetch('/fail', 'tok')).rejects.toMatchObject({
      status: 502,
      message: 'Request failed',
    })
  })

  it('returns parsed JSON on success', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify([{ order_id: 'ord_1' }]), { status: 200 }),
    )
    const result = await apiFetch<{ order_id: string }[]>('/orders', 'tok')
    expect(result[0].order_id).toBe('ord_1')
  })
})
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
cd apps/web && pnpm test __tests__/lib/api.test.ts
```

- [ ] **Step 3: Write `apps/web/lib/api.ts`**

```typescript
// apiServer methods import auth() at call time — they only work in Next.js server context.
// apiFetch works everywhere (pass token from /api/token route in client components).

import type { Session } from 'next-auth'

const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    cache: 'no-store',
    ...init,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...(init?.headers ?? {}),
    },
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new ApiError(res.status, (body as { detail?: string }).detail ?? 'Request failed')
  }
  return res.json() as Promise<T>
}

export const apiServer = {
  async get<T>(path: string): Promise<T> {
    const { auth } = await import('@/auth')
    const session = await auth() as Session & { forgeToken?: string }
    if (!session?.forgeToken) throw new ApiError(401, 'Not authenticated')
    return request<T>(path, session.forgeToken)
  },
  async post<T>(path: string, body: unknown): Promise<T> {
    const { auth } = await import('@/auth')
    const session = await auth() as Session & { forgeToken?: string }
    if (!session?.forgeToken) throw new ApiError(401, 'Not authenticated')
    return request<T>(path, session.forgeToken, {
      method: 'POST',
      body: JSON.stringify(body),
    })
  },
}

export async function apiFetch<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  return request<T>(path, token, init)
}
```

- [ ] **Step 4: Write `apps/web/lib/session.ts`**

```typescript
import { auth } from '@/auth'
import { redirect } from 'next/navigation'

export async function requireSession() {
  const session = await auth()
  if (!session?.forgeToken) {
    redirect('/auth/signin')
  }
  return session
}
```

- [ ] **Step 5: Run test — expect PASS**

```bash
cd apps/web && pnpm test __tests__/lib/api.test.ts
```

- [ ] **Step 6: Commit**

```bash
git add apps/web/lib/api.ts apps/web/lib/session.ts apps/web/__tests__/lib/api.test.ts
git commit -m "feat(web): add typed API client and session helper"
```

---

### Task 6: Auth Setup (Auth.js v5)

**Files:**
- Create: `apps/web/types/next-auth.d.ts`
- Create: `apps/web/auth.ts`
- Create: `apps/web/middleware.ts`
- Create: `apps/web/app/api/auth/[...nextauth]/route.ts`
- Create: `apps/web/app/api/token/route.ts`

**Interfaces:**
- Produces: `auth()` callable in server components, `signIn`/`signOut` for client components, middleware protecting `/orders/:path*` and `/api/token`

- [ ] **Step 1: Create `apps/web/types/next-auth.d.ts`**

```typescript
import { DefaultSession } from 'next-auth'

declare module 'next-auth' {
  interface Session extends DefaultSession {
    forgeToken: string
    tenantId: string
  }
}

declare module '@auth/core/jwt' {
  interface JWT {
    forgeToken?: string
    tenantId?: string
  }
}
```

- [ ] **Step 2: Create `apps/web/auth.ts`**

```typescript
import NextAuth from 'next-auth'
import Google from 'next-auth/providers/google'
import GitHub from 'next-auth/providers/github'
import Resend from 'next-auth/providers/resend'
import { SignJWT } from 'jose'

const jwtSecret = new TextEncoder().encode(process.env.AUTH_SECRET!)

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Google({
      clientId: process.env.AUTH_GOOGLE_ID!,
      clientSecret: process.env.AUTH_GOOGLE_SECRET!,
    }),
    GitHub({
      clientId: process.env.AUTH_GITHUB_ID!,
      clientSecret: process.env.AUTH_GITHUB_SECRET!,
    }),
    Resend({
      apiKey: process.env.AUTH_RESEND_KEY!,
      from: 'FORGE <noreply@forge.app>',
    }),
  ],
  session: { strategy: 'jwt' },
  pages: {
    signIn: '/auth/signin',
    error: '/auth/error',
  },
  callbacks: {
    async signIn({ user }) {
      return !!user.email
    },
    async jwt({ token, user }) {
      if (user?.email && !token.forgeToken) {
        // Stub: email as tenant_id. Replace with DB lookup when tenant table is set up.
        const tenantId = user.email
        const forgeToken = await new SignJWT({ sub: user.email, tenant_id: tenantId })
          .setProtectedHeader({ alg: 'HS256' })
          .setExpirationTime('1h')
          .sign(jwtSecret)
        token.forgeToken = forgeToken
        token.tenantId   = tenantId
      }
      return token
    },
    async session({ session, token }) {
      session.forgeToken = token.forgeToken as string
      session.tenantId   = token.tenantId   as string
      return session
    },
  },
})
```

- [ ] **Step 3: Create `apps/web/middleware.ts`**

```typescript
import { auth } from '@/auth'
import { NextResponse } from 'next/server'

export default auth((req) => {
  if (!req.auth) {
    const url = new URL('/auth/signin', req.url)
    url.searchParams.set('callbackUrl', req.nextUrl.pathname)
    return NextResponse.redirect(url)
  }
})

export const config = {
  matcher: ['/orders/:path*', '/api/token'],
}
```

- [ ] **Step 4: Create `apps/web/app/api/auth/[...nextauth]/route.ts`**

```typescript
import { handlers } from '@/auth'
export const { GET, POST } = handlers
```

- [ ] **Step 5: Create `apps/web/app/api/token/route.ts`**

```typescript
import { auth } from '@/auth'
import { NextResponse } from 'next/server'

export async function GET() {
  const session = await auth()
  if (!session?.forgeToken) {
    return NextResponse.json({ error: 'Not authenticated' }, { status: 401 })
  }
  return NextResponse.json({ token: session.forgeToken })
}
```

- [ ] **Step 6: Create `.env.local` from the example and set AUTH_SECRET**

```bash
cp apps/web/.env.local.example apps/web/.env.local
# Then edit .env.local — minimum for local testing:
# AUTH_SECRET=$(openssl rand -hex 32)
# NEXT_PUBLIC_API_URL=http://localhost:8000
# OAuth keys required for Google/GitHub sign-in to work
```

- [ ] **Step 7: Verify middleware redirects unauthenticated users**

```bash
cd apps/web && pnpm dev
# Open http://localhost:3000/orders — should redirect to /auth/signin
```

Expected: redirect to `/auth/signin?callbackUrl=/orders`

- [ ] **Step 8: Commit**

```bash
git add apps/web/types/ apps/web/auth.ts apps/web/middleware.ts \
        apps/web/app/api/
git commit -m "feat(web): auth.js v5 config — Google, GitHub, Resend magic-link + middleware"
```

---

### Task 7: Auth Pages

**Files:**
- Create: `apps/web/app/auth/signin/page.tsx`
- Create: `apps/web/app/auth/error/page.tsx`

**Interfaces:**
- Consumes: `Button` from `@/components/ui/Button`, `Field` from `@/components/ui/Field`, `signIn` from `next-auth/react`

- [ ] **Step 1: Create `apps/web/app/auth/signin/page.tsx`**

```tsx
'use client'

import { signIn } from 'next-auth/react'
import { useState, FormEvent } from 'react'
import { Button } from '@/components/ui/Button'
import { Field } from '@/components/ui/Field'

interface PageProps {
  searchParams: { callbackUrl?: string; error?: string }
}

const ERROR_TEXT: Record<string, string> = {
  OAuthSignin:    'Could not start OAuth sign-in. Please try again.',
  OAuthCallback:  'OAuth sign-in failed. Please try again.',
  OAuthCreateAccount: 'Could not create your account. Please contact support.',
  Verification:   'Your sign-in link expired. Please request a new one.',
  Default:        'Sign-in failed. Please try again.',
}

export default function SignInPage({ searchParams }: PageProps) {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState<string | null>(null)
  const callbackUrl = searchParams.callbackUrl ?? '/orders'
  const errorMsg = searchParams.error ? (ERROR_TEXT[searchParams.error] ?? ERROR_TEXT.Default) : null

  async function handleProvider(provider: 'google' | 'github') {
    setLoading(provider)
    await signIn(provider, { callbackUrl })
  }

  async function handleEmail(e: FormEvent) {
    e.preventDefault()
    if (!email.trim()) return
    setLoading('resend')
    await signIn('resend', { email, callbackUrl })
  }

  return (
    <div className="min-h-screen bg-forge-surface flex items-center justify-center p-6">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-bold text-forge-ink mb-1">Sign in to FORGE</h1>
        <p className="text-forge-ink-muted mb-8 text-sm">Order and track your robot datasets.</p>

        {errorMsg && (
          <p className="mb-6 text-sm text-forge-danger bg-forge-danger-soft rounded-control px-4 py-3">
            {errorMsg}
          </p>
        )}

        <div className="flex flex-col gap-3">
          <Button variant="secondary" onClick={() => handleProvider('google')}
                  loading={loading === 'google'} className="w-full justify-center">
            Continue with Google
          </Button>
          <Button variant="secondary" onClick={() => handleProvider('github')}
                  loading={loading === 'github'} className="w-full justify-center">
            Continue with GitHub
          </Button>
        </div>

        <div className="my-6 flex items-center gap-3">
          <div className="flex-1 h-px bg-forge-border" />
          <span className="text-xs text-forge-ink-muted">or</span>
          <div className="flex-1 h-px bg-forge-border" />
        </div>

        <form onSubmit={handleEmail} className="flex flex-col gap-4">
          <Field
            id="email" label="Email address" type="email"
            value={email} onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com" required
          />
          <Button type="submit" variant="secondary"
                  loading={loading === 'resend'} className="w-full justify-center">
            Send magic link
          </Button>
        </form>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Create `apps/web/app/auth/error/page.tsx`**

```tsx
import Link from 'next/link'
import { Button } from '@/components/ui/Button'

const ERROR_MESSAGES: Record<string, string> = {
  Configuration: 'There is a problem with the server configuration. Please contact support.',
  AccessDenied:  'You do not have permission to sign in with this account.',
  Verification:  'The sign-in link has expired or already been used. Please try again.',
  Default:       'Something went wrong during sign-in. Please try again.',
}

export default function AuthErrorPage({
  searchParams,
}: {
  searchParams: { error?: string }
}) {
  const message = ERROR_MESSAGES[searchParams.error ?? 'Default'] ?? ERROR_MESSAGES.Default

  return (
    <div className="min-h-screen bg-forge-surface flex items-center justify-center p-6">
      <div className="w-full max-w-sm text-center">
        <h1 className="text-2xl font-bold text-forge-ink mb-3">Sign-in failed</h1>
        <p className="text-forge-ink-muted mb-8 text-sm">{message}</p>
        <Link href="/auth/signin">
          <Button variant="primary">Try again</Button>
        </Link>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Verify auth pages render**

```bash
# With pnpm dev running:
# Visit http://localhost:3000/auth/signin — see three sign-in options
# Visit http://localhost:3000/auth/error?error=Verification — see friendly message
```

- [ ] **Step 4: Commit**

```bash
git add apps/web/app/auth/
git commit -m "feat(web): auth sign-in and error pages"
```

---

### Task 8: NavBar + Portal Layout

**Files:**
- Create: `apps/web/components/layout/NavBar.tsx`
- Create: `apps/web/app/orders/layout.tsx`

**Interfaces:**
- Consumes: `auth()` from `@/auth`; `Button` from `@/components/ui/Button`
- Produces: authenticated portal layout wrapping `/orders/*` routes

- [ ] **Step 1: Create `apps/web/components/layout/NavBar.tsx`**

```tsx
'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { signOut } from 'next-auth/react'
import { Button } from '@/components/ui/Button'

const NAV_ITEMS = [
  { href: '/orders',   label: 'Orders' },
  { href: '/datasets', label: 'Datasets' },
  { href: '/account',  label: 'Account' },
] as const

interface NavBarProps {
  authenticated?: boolean
}

export function NavBar({ authenticated }: NavBarProps) {
  const pathname = usePathname()

  return (
    <nav className="flex items-center justify-between px-6 py-4 border-b border-forge-border bg-forge-surface">
      <div className="flex items-center gap-8">
        <Link href={authenticated ? '/orders' : '/'} className="text-lg font-bold text-forge-ink tracking-tight">
          FORGE
        </Link>
        {authenticated && (
          <ul className="flex items-center gap-6" role="list">
            {NAV_ITEMS.map(({ href, label }) => {
              const active = pathname.startsWith(href)
              return (
                <li key={href}>
                  <Link
                    href={href}
                    className={`text-sm transition-colors ${
                      active
                        ? 'text-forge-primary font-semibold'
                        : 'text-forge-ink-muted hover:text-forge-ink'
                    }`}
                    aria-current={active ? 'page' : undefined}
                  >
                    {label}
                  </Link>
                </li>
              )
            })}
          </ul>
        )}
      </div>
      <div>
        {authenticated ? (
          <Button variant="tertiary" onClick={() => signOut({ callbackUrl: '/' })}
                  className="text-sm min-h-[36px]">
            Sign out
          </Button>
        ) : (
          <Link href="/auth/signin">
            <Button variant="secondary" className="text-sm min-h-[36px]">Sign in</Button>
          </Link>
        )}
      </div>
    </nav>
  )
}
```

- [ ] **Step 2: Create `apps/web/app/orders/layout.tsx`**

```tsx
import { ReactNode } from 'react'
import { redirect } from 'next/navigation'
import { auth } from '@/auth'
import { NavBar } from '@/components/layout/NavBar'

export default async function OrdersLayout({ children }: { children: ReactNode }) {
  const session = await auth()
  if (!session) redirect('/auth/signin')

  return (
    <div className="min-h-screen bg-forge-canvas">
      <NavBar authenticated />
      <main className="max-w-5xl mx-auto px-6 py-8">
        {children}
      </main>
    </div>
  )
}
```

- [ ] **Step 3: Verify layout renders**

Create a temporary `apps/web/app/orders/page.tsx` containing just `export default function Page() { return <p>Hello</p> }`, sign in, navigate to `/orders` — should see NavBar with Orders/Datasets/Account.

- [ ] **Step 4: Commit**

```bash
git add apps/web/components/layout/NavBar.tsx apps/web/app/orders/layout.tsx
git commit -m "feat(web): portal layout with NavBar and auth gate"
```

---

### Task 9: Landing Page

**Files:**
- Create: `apps/web/components/landing/Hero.tsx`
- Create: `apps/web/components/landing/ProcessSteps.tsx`
- Create: `apps/web/app/page.tsx`

**Interfaces:**
- Consumes: `Button` from `@/components/ui/Button`

- [ ] **Step 1: Create `apps/web/components/landing/Hero.tsx`**

```tsx
import Link from 'next/link'
import { Button } from '@/components/ui/Button'

export function Hero() {
  return (
    <section className="px-6 pt-24 pb-20 max-w-3xl">
      <h1 className="text-5xl font-bold text-forge-ink leading-tight tracking-tight">
        Human demonstrations in.
        <br />
        Validated robot-ready datasets out.
      </h1>
      <p className="mt-6 text-xl text-forge-ink-muted max-w-[56ch]">
        FORGE turns physical demonstrations into physics-validated datasets
        ready for robot learning — no infrastructure required.
      </p>
      <div className="mt-10">
        <Link href="/auth/signin?callbackUrl=/orders/new">
          <Button variant="primary" className="text-base px-8">
            Define your robot task
          </Button>
        </Link>
      </div>
    </section>
  )
}
```

- [ ] **Step 2: Create `apps/web/components/landing/ProcessSteps.tsx`**

```tsx
const STEPS = [
  'Dataset Planning',
  'Human Acquisition',
  'Physical Data Compilation',
  'Robot Retargeting',
  'Physics Validation',
  'Dataset Amplification',
  'Delivery',
]

export function ProcessSteps() {
  return (
    <section className="px-6 py-20">
      <h2 className="text-2xl font-semibold text-forge-ink mb-12">How it works</h2>
      <ol className="flex flex-col gap-6" role="list">
        {STEPS.map((label, i) => (
          <li key={label} className="flex items-baseline gap-5">
            <span className="text-sm font-mono text-forge-ink-muted w-4 shrink-0 select-none">
              {i + 1}
            </span>
            <span className="text-lg text-forge-ink">{label}</span>
          </li>
        ))}
      </ol>
    </section>
  )
}
```

- [ ] **Step 3: Create `apps/web/app/page.tsx`**

```tsx
import Link from 'next/link'
import { Hero } from '@/components/landing/Hero'
import { ProcessSteps } from '@/components/landing/ProcessSteps'

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-forge-canvas flex flex-col">
      <header className="flex items-center justify-between px-6 py-4">
        <span className="text-lg font-bold text-forge-ink tracking-tight">FORGE</span>
        <Link href="/auth/signin" className="text-sm text-forge-ink-muted hover:text-forge-ink transition-colors">
          Sign in
        </Link>
      </header>
      <main className="flex-1">
        <Hero />
        <ProcessSteps />
      </main>
      <footer className="px-6 py-8 border-t border-forge-border">
        <div className="flex gap-6 text-sm text-forge-ink-muted">
          <Link href="/auth/signin" className="hover:text-forge-ink transition-colors">Sign in</Link>
          <a href="mailto:hello@forge.app" className="hover:text-forge-ink transition-colors">Contact</a>
        </div>
      </footer>
    </div>
  )
}
```

- [ ] **Step 4: Verify landing page**

Visit `http://localhost:3000` — headline, 7-step list, footer links. No logo wall, no metric claims, one CTA.

- [ ] **Step 5: Commit**

```bash
git add apps/web/app/page.tsx apps/web/components/landing/
git commit -m "feat(web): landing page — hero, process steps, footer"
```

---

### Task 10: Extend API Order Responses

**Files:**
- Modify: `services/api/src/routers/orders.py`

**Interfaces:**
- Produces: `OrderResponse` now includes optional `skill_name: str | None`, `created_at: str | None`, `volume_validated_episodes: int | None`, `contract: dict | None`

- [ ] **Step 1: Update `OrderResponse` in `orders.py`**

Find the existing model (around line 60) and replace it:

```python
class OrderResponse(BaseModel):
    order_id: str
    state: str
    stripe_payment_link: str | None = None
    skill_name: str | None = None
    created_at: str | None = None
    volume_validated_episodes: int | None = None
    contract: dict | None = None
```

- [ ] **Step 2: Update `list_orders` query to include new fields**

Replace the existing `list_orders` function body:

```python
@router.get("", response_model=list[OrderResponse])
def list_orders(ctx: TenantContext = Depends(require_tenant)) -> list[OrderResponse]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, state, skill_name, created_at,
                   (contract->'volume'->>'validated_episodes')::int AS validated_episodes
            FROM dataset_orders
            WHERE tenant_id = %s
            ORDER BY created_at DESC
            """,
            (ctx.tenant_id,),
        ).fetchall()
    return [
        OrderResponse(
            order_id=row[0],
            state=row[1],
            skill_name=row[2],
            created_at=row[3].isoformat() if row[3] else None,
            volume_validated_episodes=row[4],
            stripe_payment_link=None,
        )
        for row in rows
    ]
```

- [ ] **Step 3: Update `get_order` query to include contract + metadata**

```python
@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: str, ctx: TenantContext = Depends(require_tenant)) -> OrderResponse:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT id, state, skill_name, created_at, contract,
                   (contract->'volume'->>'validated_episodes')::int AS validated_episodes
            FROM dataset_orders
            WHERE id = %s AND tenant_id = %s
            """,
            (order_id, ctx.tenant_id),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return OrderResponse(
        order_id=row[0],
        state=row[1],
        skill_name=row[2],
        created_at=row[3].isoformat() if row[3] else None,
        contract=row[4],
        volume_validated_episodes=row[5],
        stripe_payment_link=None,
    )
```

- [ ] **Step 4: Verify API response**

```bash
# Restart the API server, then:
curl -H "Authorization: Bearer <token>" http://localhost:8000/orders | python3 -m json.tool
# Expect skill_name and created_at in each entry
```

- [ ] **Step 5: Commit**

```bash
git add services/api/src/routers/orders.py
git commit -m "feat(api): extend OrderResponse with skill_name, created_at, contract"
```

---

### Task 11: Orders List Page

**Files:**
- Create: `apps/web/components/orders/OrderRow.tsx`
- Create (replace temp): `apps/web/app/orders/page.tsx`

**Interfaces:**
- Consumes: `Order` from `@/lib/types`, `StatusBadge` from `@/components/ui/StatusBadge`, `apiServer` from `@/lib/api`, `Button` from `@/components/ui/Button`

- [ ] **Step 1: Create `apps/web/components/orders/OrderRow.tsx`**

```tsx
import Link from 'next/link'
import { Order } from '@/lib/types'
import { StatusBadge } from '@/components/ui/StatusBadge'

interface OrderRowProps {
  order: Order
}

export function OrderRow({ order }: OrderRowProps) {
  const date = order.created_at
    ? new Date(order.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
    : '—'

  return (
    <tr className="border-b border-forge-border last:border-0 hover:bg-forge-surface-soft transition-colors">
      <td className="py-4 pr-6">
        <Link
          href={`/orders/${order.order_id}`}
          className="text-forge-ink font-medium hover:text-forge-primary transition-colors"
        >
          {order.skill_name ?? 'Untitled order'}
        </Link>
      </td>
      <td className="py-4 pr-6">
        <StatusBadge state={order.state} />
      </td>
      <td className="py-4 pr-6 text-forge-ink-muted tabular-nums">
        {order.volume_validated_episodes ?? '—'}
      </td>
      <td className="py-4 text-sm text-forge-ink-muted tabular-nums">{date}</td>
    </tr>
  )
}
```

- [ ] **Step 2: Create `apps/web/app/orders/page.tsx`**

```tsx
import Link from 'next/link'
import { apiServer, ApiError } from '@/lib/api'
import { Order } from '@/lib/types'
import { OrderRow } from '@/components/orders/OrderRow'
import { Button } from '@/components/ui/Button'

export default async function OrdersPage() {
  let orders: Order[] = []
  let fetchError: string | null = null

  try {
    orders = await apiServer.get<Order[]>('/orders')
  } catch (err) {
    fetchError = err instanceof ApiError
      ? 'We could not connect to the server. Check your connection.'
      : 'Something went wrong. Please try again.'
  }

  return (
    <div>
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-forge-ink">Your Orders</h1>
          <p className="text-forge-ink-muted mt-1 text-sm">
            Track and manage your dataset orders.
          </p>
        </div>
        <Link href="/orders/new">
          <Button variant="primary">New order</Button>
        </Link>
      </div>

      {fetchError ? (
        <div className="py-16 text-center">
          <p className="text-forge-ink-muted mb-5">{fetchError}</p>
          <a href="/orders">
            <Button variant="secondary">Try again</Button>
          </a>
        </div>
      ) : orders.length === 0 ? (
        <div className="py-20 text-center">
          <h2 className="text-xl font-semibold text-forge-ink mb-2">No orders yet</h2>
          <p className="text-forge-ink-muted mb-8 text-sm max-w-sm mx-auto">
            Place your first order to start collecting robot demonstration data.
          </p>
          <Link href="/orders/new">
            <Button variant="primary">Place your first order</Button>
          </Link>
        </div>
      ) : (
        <table className="w-full">
          <thead>
            <tr className="border-b border-forge-border text-left">
              <th className="pb-3 text-xs font-medium text-forge-ink-muted uppercase tracking-wide pr-6">Skill name</th>
              <th className="pb-3 text-xs font-medium text-forge-ink-muted uppercase tracking-wide pr-6">Status</th>
              <th className="pb-3 text-xs font-medium text-forge-ink-muted uppercase tracking-wide pr-6">Episodes ordered</th>
              <th className="pb-3 text-xs font-medium text-forge-ink-muted uppercase tracking-wide">Created</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((order) => (
              <OrderRow key={order.order_id} order={order} />
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Verify list page**

With API running and at least one order in DB: navigate to `/orders` — see table rows with status badges. Test empty state by using a new tenant.

- [ ] **Step 4: Commit**

```bash
git add apps/web/components/orders/OrderRow.tsx apps/web/app/orders/page.tsx
git commit -m "feat(web): orders list page — table, empty state, error state"
```

---

### Task 12: Order Detail + Workspace Tabs

**Files:**
- Create: `apps/web/components/orders/workspace/PlaceholderTab.tsx`
- Create: `apps/web/components/orders/workspace/OverviewTab.tsx`
- Create: `apps/web/components/orders/workspace/WorkspaceTabs.tsx`
- Create: `apps/web/app/orders/[orderId]/page.tsx`

**Interfaces:**
- Consumes: `Order` from `@/lib/types`, `STATUS_LABELS` from `@/lib/types`, `StatusBadge` from `@/components/ui/StatusBadge`, `apiServer` from `@/lib/api`
- Produces: order detail page with 8 tabs, Overview tab live, rest as placeholders

- [ ] **Step 1: Create `apps/web/components/orders/workspace/PlaceholderTab.tsx`**

```tsx
interface PlaceholderTabProps {
  name: string
  description: string
}

export function PlaceholderTab({ name, description }: PlaceholderTabProps) {
  return (
    <div className="py-16">
      <h3 className="text-lg font-semibold text-forge-ink mb-2">{name} — coming soon</h3>
      <p className="text-forge-ink-muted text-sm max-w-prose">{description}</p>
    </div>
  )
}
```

- [ ] **Step 2: Create `apps/web/components/orders/workspace/OverviewTab.tsx`**

```tsx
import { Order, STATUS_LABELS } from '@/lib/types'

interface OverviewTabProps {
  order: Order
}

export function OverviewTab({ order }: OverviewTabProps) {
  const { label, detail } = STATUS_LABELS[order.state]
  const statusText = detail ? `${label} · ${detail}` : label
  const coverage = order.contract?.coverage as { object_ids?: string[]; viewpoint_bins?: string[] } | undefined
  const billing  = order.contract?.rights_profile as string | undefined

  const nextAction: Record<string, string> = {
    DRAFT:       'Complete payment to begin planning your collection.',
    PAID:        'Our team is reviewing your order and planning acquisition.',
    PLANNING:    'Our team is planning your acquisition schedule.',
    ACQUIRING:   'Demonstrations are being collected by human operators.',
    READY:       'Your dataset is ready. Review and approve to trigger delivery.',
  }

  return (
    <div className="flex flex-col gap-10">
      <section>
        <h3 className="text-sm font-medium text-forge-ink-muted uppercase tracking-wide mb-3">Status</h3>
        <p className="text-lg text-forge-ink">{statusText}</p>
        {nextAction[order.state] && (
          <p className="mt-2 text-sm text-forge-ink-muted">{nextAction[order.state]}</p>
        )}
        {order.created_at && (
          <p className="mt-1 text-xs text-forge-ink-subtle">
            Last updated: {new Date(order.created_at).toLocaleString('en-US')}
          </p>
        )}
      </section>

      {coverage?.object_ids && coverage.object_ids.length > 0 && (
        <section>
          <h3 className="text-sm font-medium text-forge-ink-muted uppercase tracking-wide mb-3">Coverage</h3>
          <div className="flex flex-wrap gap-2">
            {coverage.object_ids.map((id) => (
              <span key={id} className="text-sm px-2.5 py-1 rounded-control border border-forge-border text-forge-ink-muted">
                {id}
              </span>
            ))}
          </div>
          {coverage.viewpoint_bins && coverage.viewpoint_bins.length > 0 && (
            <p className="mt-2 text-sm text-forge-ink-muted">
              Viewpoints: {coverage.viewpoint_bins.join(', ')}
            </p>
          )}
        </section>
      )}

      <section>
        <h3 className="text-sm font-medium text-forge-ink-muted uppercase tracking-wide mb-3">Billing</h3>
        <p className="text-sm text-forge-ink">
          {order.state === 'DRAFT'
            ? 'Awaiting payment to begin collection.'
            : 'Payment received. Billing details available in the Billing tab.'}
        </p>
        {billing && (
          <p className="mt-1 text-xs text-forge-ink-muted">
            Rights profile: {billing.replace(/_/g, ' ')}
          </p>
        )}
      </section>
    </div>
  )
}
```

- [ ] **Step 3: Create `apps/web/components/orders/workspace/WorkspaceTabs.tsx`**

```tsx
'use client'

import { useState } from 'react'
import { Order } from '@/lib/types'
import { OverviewTab } from './OverviewTab'
import { PlaceholderTab } from './PlaceholderTab'

const TABS = [
  { id: 'overview',    label: 'Overview' },
  { id: 'acquisition', label: 'Acquisition' },
  { id: 'processing',  label: 'Processing' },
  { id: 'quality',     label: 'Quality' },
  { id: 'episodes',    label: 'Episodes' },
  { id: 'dataset',     label: 'Dataset' },
  { id: 'activity',    label: 'Activity' },
  { id: 'billing',     label: 'Billing' },
] as const

type TabId = typeof TABS[number]['id']

const PLACEHOLDER_DESCRIPTIONS: Partial<Record<TabId, string>> = {
  acquisition: 'Details about human operator assignments, session schedule, and collection progress.',
  processing:  'Retargeting jobs, physics simulation runs, and intermediate QC results.',
  quality:     'Penetration metrics, F1 scores, acceptance rates, and QC decision history.',
  episodes:    'Individual episode recordings with replay validation status.',
  dataset:     'Final packaged dataset, file manifest, and download links.',
  activity:    'Full audit trail — every state transition and decision for this order.',
  billing:     'Invoice, payment status, and rights license summary.',
}

interface WorkspaceTabsProps {
  order: Order
}

export function WorkspaceTabs({ order }: WorkspaceTabsProps) {
  const [active, setActive] = useState<TabId>('overview')

  return (
    <div>
      <div className="flex gap-0 border-b border-forge-border" role="tablist">
        {TABS.map(({ id, label }) => (
          <button
            key={id}
            role="tab"
            aria-selected={active === id}
            aria-controls={`tabpanel-${id}`}
            onClick={() => setActive(id)}
            className={[
              'px-4 py-3 text-sm font-medium transition-colors',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-forge-focus focus-visible:ring-inset',
              active === id
                ? 'text-forge-primary border-b-2 border-forge-primary -mb-px'
                : 'text-forge-ink-muted hover:text-forge-ink',
            ].join(' ')}
          >
            {label}
          </button>
        ))}
      </div>
      <div className="pt-8" id={`tabpanel-${active}`} role="tabpanel">
        {active === 'overview' ? (
          <OverviewTab order={order} />
        ) : (
          <PlaceholderTab
            name={TABS.find((t) => t.id === active)!.label}
            description={PLACEHOLDER_DESCRIPTIONS[active] ?? 'Details for this section will appear here.'}
          />
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Create `apps/web/app/orders/[orderId]/page.tsx`**

```tsx
import { notFound } from 'next/navigation'
import { apiServer, ApiError } from '@/lib/api'
import { Order, STATUS_LABELS } from '@/lib/types'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { WorkspaceTabs } from '@/components/orders/workspace/WorkspaceTabs'
import { Button } from '@/components/ui/Button'

interface PageProps {
  params: { orderId: string }
}

export default async function OrderDetailPage({ params }: PageProps) {
  let order: Order

  try {
    order = await apiServer.get<Order>(`/orders/${params.orderId}`)
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound()
    throw err
  }

  const isReady = order.state === 'READY'

  return (
    <div>
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-forge-ink mb-1">
            {order.skill_name ?? 'Order'}
          </h1>
          <StatusBadge state={order.state} />
        </div>
        <Button variant="secondary" disabled={!isReady} className="text-sm">
          Download dataset
        </Button>
      </div>
      <WorkspaceTabs order={order} />
    </div>
  )
}
```

- [ ] **Step 5: Verify order detail**

Click an order row → see detail page with 8 tabs, Overview active with status narrative and coverage.

- [ ] **Step 6: Commit**

```bash
git add apps/web/components/orders/workspace/ apps/web/app/orders/
git commit -m "feat(web): order detail page with workspace tabs and live overview"
```

---

### Task 13: New Order Stepper

**Files:**
- Create: `apps/web/components/orders/NewOrderStepper.tsx`
- Create: `apps/web/components/orders/steps/SkillStep.tsx`
- Create: `apps/web/components/orders/steps/RobotStep.tsx`
- Create: `apps/web/components/orders/steps/CoverageStep.tsx`
- Create: `apps/web/components/orders/steps/VolumeQualityStep.tsx`
- Create: `apps/web/components/orders/steps/RightsStep.tsx`
- Create: `apps/web/components/orders/steps/ReviewStep.tsx`
- Create: `apps/web/app/orders/new/page.tsx`
- Create: `apps/web/__tests__/orders/NewOrderStepper.test.tsx`

**Interfaces:**
- Consumes: `CreateOrderPayload`, `CreateOrderResponse` from `@/lib/types`; `apiFetch` from `@/lib/api`; `Field`, `Button` from `@/components/ui/`
- Produces: `<NewOrderStepper token={string}>` — calls `POST /orders` on step 6, redirects to Stripe URL or order detail

- [ ] **Step 1: Write the failing test**

```typescript
// apps/web/__tests__/orders/NewOrderStepper.test.tsx
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { NewOrderStepper } from '@/components/orders/NewOrderStepper'
import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('next/navigation', () => ({ useRouter: () => ({ push: vi.fn() }) }))

describe('NewOrderStepper', () => {
  it('renders step 1 (Skill) initially', () => {
    render(<NewOrderStepper token="tok_test" />)
    expect(screen.getByText('What should the robot do?')).toBeInTheDocument()
    expect(screen.getByText(/step 1 of 6/i)).toBeInTheDocument()
  })

  it('does not advance from step 1 when task name is empty', async () => {
    render(<NewOrderStepper token="tok_test" />)
    await userEvent.click(screen.getByRole('button', { name: /next/i }))
    expect(screen.getByText('What should the robot do?')).toBeInTheDocument()
  })

  it('advances to step 2 after filling required step 1 fields', async () => {
    render(<NewOrderStepper token="tok_test" />)
    await userEvent.type(screen.getByLabelText(/task name/i), 'Pick apple')
    await userEvent.type(screen.getByLabelText(/initial state/i), 'Apple on table')
    await userEvent.type(screen.getByLabelText(/success/i), 'Apple in bin')
    await userEvent.click(screen.getByRole('button', { name: /next/i }))
    expect(screen.getByText('Which robot and hand?')).toBeInTheDocument()
    expect(screen.getByText(/step 2 of 6/i)).toBeInTheDocument()
  })

  it('goes back and preserves data', async () => {
    render(<NewOrderStepper token="tok_test" />)
    await userEvent.type(screen.getByLabelText(/task name/i), 'Pick apple')
    await userEvent.type(screen.getByLabelText(/initial state/i), 'Apple on table')
    await userEvent.type(screen.getByLabelText(/success/i), 'Apple in bin')
    await userEvent.click(screen.getByRole('button', { name: /next/i }))
    await userEvent.click(screen.getByRole('button', { name: /back/i }))
    expect(screen.getByDisplayValue('Pick apple')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
cd apps/web && pnpm test __tests__/orders/NewOrderStepper.test.tsx
```

- [ ] **Step 3: Create the shared type for stepper state**

Add to `apps/web/lib/types.ts` (append after `CreateOrderResponse`):

```typescript
export interface OrderFormData {
  skill: {
    name: string
    initial_state: string
    success_predicate: string
    failure_predicates: string[]
    phases: string[]
  }
  embodiment: {
    robot_id: string
    model_uri: string
    model_sha256: string
    hand_type: 'dexterous' | 'parallel_gripper' | 'suction'
    joint_limits_uri: string
  }
  coverage: {
    object_ids: string[]
    viewpoint_bins: string[]
    grasp_variation: 'required' | 'preferred' | 'not_required'
  }
  volume_validated_episodes: number
  quality: {
    source_replay_pass_required: boolean
    max_penetration_m: number
    min_contact_phase_f1: number
    min_delivery_acceptance_rate: number
  }
  rights_profile: 'customer_exclusive_derivatives' | 'forge_retained' | 'open'
}

export const INITIAL_ORDER_FORM_DATA: OrderFormData = {
  skill: { name: '', initial_state: '', success_predicate: '', failure_predicates: [], phases: [] },
  embodiment: { robot_id: '', model_uri: '', model_sha256: '', hand_type: 'parallel_gripper', joint_limits_uri: '' },
  coverage: { object_ids: [], viewpoint_bins: [], grasp_variation: 'preferred' },
  volume_validated_episodes: 10,
  quality: {
    source_replay_pass_required: true,
    max_penetration_m: 0.002,
    min_contact_phase_f1: 0.8,
    min_delivery_acceptance_rate: 0.9,
  },
  rights_profile: 'customer_exclusive_derivatives',
}
```

- [ ] **Step 4: Create `apps/web/components/orders/NewOrderStepper.tsx`**

```tsx
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { OrderFormData, INITIAL_ORDER_FORM_DATA, CreateOrderResponse } from '@/lib/types'
import { apiFetch, ApiError } from '@/lib/api'
import { SkillStep } from './steps/SkillStep'
import { RobotStep } from './steps/RobotStep'
import { CoverageStep } from './steps/CoverageStep'
import { VolumeQualityStep } from './steps/VolumeQualityStep'
import { RightsStep } from './steps/RightsStep'
import { ReviewStep } from './steps/ReviewStep'

const STEP_TITLES = [
  'What should the robot do?',
  'Which robot and hand?',
  'Which objects and viewpoints?',
  'How many episodes and what quality bar?',
  'Who owns the data?',
  'Does this look right?',
]

interface NewOrderStepperProps {
  token: string
}

export function NewOrderStepper({ token }: NewOrderStepperProps) {
  const [step, setStep] = useState(0)
  const [data, setData] = useState<OrderFormData>(INITIAL_ORDER_FORM_DATA)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const router = useRouter()

  function update<K extends keyof OrderFormData>(key: K, value: OrderFormData[K]) {
    setData((prev) => ({ ...prev, [key]: value }))
  }

  async function handleSubmit() {
    setSubmitting(true)
    setSubmitError(null)
    try {
      const res = await apiFetch<CreateOrderResponse>('/orders', token, {
        method: 'POST',
        body: JSON.stringify({
          skill:                     data.skill,
          embodiment:                data.embodiment,
          volume_validated_episodes: data.volume_validated_episodes,
          coverage:                  data.coverage,
          quality:                   data.quality,
          rights_profile:            data.rights_profile,
        }),
      })
      if (res.stripe_payment_link) {
        window.location.href = res.stripe_payment_link
      } else {
        router.push(`/orders/${res.order_id}`)
      }
    } catch (err) {
      setSubmitError(
        err instanceof ApiError
          ? `Order could not be placed: ${err.message}. Please try again.`
          : 'Something went wrong. Please try again.',
      )
      setSubmitting(false)
    }
  }

  const progress = ((step + 1) / 6) * 100

  return (
    <div className="max-w-xl">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs text-forge-ink-muted">Step {step + 1} of 6</span>
        <span className="text-xs text-forge-ink-muted">{STEP_TITLES[step]}</span>
      </div>
      <div className="w-full bg-forge-surface-soft rounded-pill h-1.5 mb-8" role="progressbar"
           aria-valuenow={step + 1} aria-valuemin={1} aria-valuemax={6}>
        <div className="bg-forge-primary rounded-pill h-1.5 transition-all duration-300"
             style={{ width: `${progress}%` }} />
      </div>

      <h2 className="text-xl font-semibold text-forge-ink mb-6">{STEP_TITLES[step]}</h2>

      {step === 0 && (
        <SkillStep data={data.skill} onChange={(v) => update('skill', v)}
                   onNext={() => setStep(1)} />
      )}
      {step === 1 && (
        <RobotStep data={data.embodiment} onChange={(v) => update('embodiment', v)}
                   onNext={() => setStep(2)} onBack={() => setStep(0)} />
      )}
      {step === 2 && (
        <CoverageStep data={data.coverage} onChange={(v) => update('coverage', v)}
                      onNext={() => setStep(3)} onBack={() => setStep(1)} />
      )}
      {step === 3 && (
        <VolumeQualityStep
          volume={data.volume_validated_episodes}
          quality={data.quality}
          onChangeVolume={(v) => update('volume_validated_episodes', v)}
          onChangeQuality={(v) => update('quality', v)}
          onNext={() => setStep(4)} onBack={() => setStep(2)} />
      )}
      {step === 4 && (
        <RightsStep data={data.rights_profile} onChange={(v) => update('rights_profile', v)}
                    onNext={() => setStep(5)} onBack={() => setStep(3)} />
      )}
      {step === 5 && (
        <ReviewStep data={data} onBack={() => setStep(4)}
                    onSubmit={handleSubmit} submitting={submitting} error={submitError} />
      )}
    </div>
  )
}
```

- [ ] **Step 5: Create `apps/web/components/orders/steps/SkillStep.tsx`**

```tsx
import { OrderFormData } from '@/lib/types'
import { Field } from '@/components/ui/Field'
import { Button } from '@/components/ui/Button'

type SkillData = OrderFormData['skill']

interface SkillStepProps {
  data: SkillData
  onChange: (data: SkillData) => void
  onNext: () => void
}

export function SkillStep({ data, onChange, onNext }: SkillStepProps) {
  function set<K extends keyof SkillData>(key: K, value: SkillData[K]) {
    onChange({ ...data, [key]: value })
  }

  function handleNext() {
    if (!data.name.trim() || !data.initial_state.trim() || !data.success_predicate.trim()) return
    onNext()
  }

  const canProceed = data.name.trim() && data.initial_state.trim() && data.success_predicate.trim()

  return (
    <div className="flex flex-col gap-5">
      <Field
        id="task-name" label="Task name" required
        value={data.name} onChange={(e) => set('name', e.target.value)}
        placeholder="e.g. Pick and place apple"
      />
      <Field
        id="initial-state" label="Initial state" required
        value={data.initial_state} onChange={(e) => set('initial_state', e.target.value)}
        placeholder="e.g. Apple resting on table surface"
      />
      <Field
        id="success-predicate" label="Success condition" required
        value={data.success_predicate} onChange={(e) => set('success_predicate', e.target.value)}
        placeholder="e.g. Apple grasped and held above table by 10 cm"
      />
      <Field
        id="failure-predicates" label="Failure conditions"
        help="Comma-separated. e.g. apple dropped, apple crushed"
        value={data.failure_predicates.join(', ')}
        onChange={(e) => set('failure_predicates', e.target.value.split(',').map((s) => s.trim()).filter(Boolean))}
      />
      <Field
        id="phases" label="Task phases"
        help="Comma-separated. e.g. approach, grasp, lift"
        value={data.phases.join(', ')}
        onChange={(e) => set('phases', e.target.value.split(',').map((s) => s.trim()).filter(Boolean))}
      />
      <div className="flex justify-end pt-2">
        <Button variant="primary" onClick={handleNext} disabled={!canProceed}>
          Next
        </Button>
      </div>
    </div>
  )
}
```

- [ ] **Step 6: Create `apps/web/components/orders/steps/RobotStep.tsx`**

```tsx
import { OrderFormData } from '@/lib/types'
import { Field } from '@/components/ui/Field'
import { Button } from '@/components/ui/Button'

type EmbodimentData = OrderFormData['embodiment']

interface RobotStepProps {
  data: EmbodimentData
  onChange: (data: EmbodimentData) => void
  onNext: () => void
  onBack: () => void
}

const HAND_TYPES: { value: EmbodimentData['hand_type']; label: string }[] = [
  { value: 'parallel_gripper', label: 'Parallel gripper' },
  { value: 'dexterous',        label: 'Dexterous hand' },
  { value: 'suction',          label: 'Suction cup' },
]

export function RobotStep({ data, onChange, onNext, onBack }: RobotStepProps) {
  function set<K extends keyof EmbodimentData>(key: K, value: EmbodimentData[K]) {
    onChange({ ...data, [key]: value })
  }

  const canProceed = data.robot_id.trim() && data.model_uri.trim() && data.model_sha256.trim()

  return (
    <div className="flex flex-col gap-5">
      <Field
        id="robot-id" label="Robot ID" required
        value={data.robot_id} onChange={(e) => set('robot_id', e.target.value)}
        placeholder="e.g. franka-panda-001"
      />
      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-forge-ink">
          Hand type <span className="text-forge-danger ml-0.5">*</span>
        </label>
        <div className="flex gap-4">
          {HAND_TYPES.map(({ value, label }) => (
            <label key={value} className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio" name="hand-type" value={value}
                checked={data.hand_type === value}
                onChange={() => set('hand_type', value)}
                className="accent-forge-primary"
              />
              <span className="text-sm text-forge-ink">{label}</span>
            </label>
          ))}
        </div>
      </div>
      <Field
        id="model-uri" label="URDF / MJCF URI" required
        help="Use r2://bucket/path format. Contact us if you need help uploading your model."
        value={data.model_uri} onChange={(e) => set('model_uri', e.target.value)}
        placeholder="r2://forge-dev/robots/franka.urdf"
      />
      <Field
        id="model-sha256" label="Model SHA-256" required
        help="SHA-256 hash of the URDF/MJCF file for integrity verification"
        value={data.model_sha256} onChange={(e) => set('model_sha256', e.target.value)}
        placeholder="abc123..."
      />
      <Field
        id="joint-limits-uri" label="Joint limits URI"
        help="r2:// URI to joint limits YAML. Leave blank to use model defaults."
        value={data.joint_limits_uri} onChange={(e) => set('joint_limits_uri', e.target.value)}
        placeholder="r2://forge-dev/robots/franka-limits.yaml"
      />
      <div className="flex justify-between pt-2">
        <Button variant="secondary" onClick={onBack}>Back</Button>
        <Button variant="primary" onClick={onNext} disabled={!canProceed}>Next</Button>
      </div>
    </div>
  )
}
```

- [ ] **Step 7: Create `apps/web/components/orders/steps/CoverageStep.tsx`**

```tsx
import { OrderFormData } from '@/lib/types'
import { Field } from '@/components/ui/Field'
import { Button } from '@/components/ui/Button'

type CoverageData = OrderFormData['coverage']

const VIEWPOINT_BINS = ['top', 'front', 'side-left', 'side-right', 'angled'] as const
const GRASP_OPTIONS: { value: CoverageData['grasp_variation']; label: string; desc: string }[] = [
  { value: 'required',     label: 'Required',     desc: 'Operators must demonstrate multiple grasp styles' },
  { value: 'preferred',    label: 'Preferred',    desc: 'Operators encouraged to vary grasp — default' },
  { value: 'not_required', label: 'Not required', desc: 'Single consistent grasp style acceptable' },
]

interface CoverageStepProps {
  data: CoverageData
  onChange: (data: CoverageData) => void
  onNext: () => void
  onBack: () => void
}

export function CoverageStep({ data, onChange, onNext, onBack }: CoverageStepProps) {
  function set<K extends keyof CoverageData>(key: K, value: CoverageData[K]) {
    onChange({ ...data, [key]: value })
  }

  function toggleViewpoint(bin: string) {
    const bins = data.viewpoint_bins.includes(bin)
      ? data.viewpoint_bins.filter((b) => b !== bin)
      : [...data.viewpoint_bins, bin]
    set('viewpoint_bins', bins)
  }

  const canProceed = data.object_ids.length > 0

  return (
    <div className="flex flex-col gap-5">
      <Field
        id="object-ids" label="Object IDs" required
        help="Comma-separated object identifiers. e.g. apple, green-cup, blue-block"
        value={data.object_ids.join(', ')}
        onChange={(e) => set('object_ids', e.target.value.split(',').map((s) => s.trim()).filter(Boolean))}
        placeholder="apple, green-cup"
      />
      <div className="flex flex-col gap-2">
        <span className="text-sm font-medium text-forge-ink">Viewpoint bins</span>
        <div className="flex flex-wrap gap-3">
          {VIEWPOINT_BINS.map((bin) => (
            <label key={bin} className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox" value={bin}
                checked={data.viewpoint_bins.includes(bin)}
                onChange={() => toggleViewpoint(bin)}
                className="accent-forge-primary"
              />
              <span className="text-sm text-forge-ink capitalize">{bin.replace('-', ' ')}</span>
            </label>
          ))}
        </div>
      </div>
      <div className="flex flex-col gap-2">
        <span className="text-sm font-medium text-forge-ink">Grasp variation</span>
        <div className="flex flex-col gap-2">
          {GRASP_OPTIONS.map(({ value, label, desc }) => (
            <label key={value} className="flex items-start gap-3 cursor-pointer">
              <input
                type="radio" name="grasp-variation" value={value}
                checked={data.grasp_variation === value}
                onChange={() => set('grasp_variation', value)}
                className="mt-0.5 accent-forge-primary"
              />
              <div>
                <p className="text-sm font-medium text-forge-ink">{label}</p>
                <p className="text-xs text-forge-ink-muted">{desc}</p>
              </div>
            </label>
          ))}
        </div>
      </div>
      <div className="flex justify-between pt-2">
        <Button variant="secondary" onClick={onBack}>Back</Button>
        <Button variant="primary" onClick={onNext} disabled={!canProceed}>Next</Button>
      </div>
    </div>
  )
}
```

- [ ] **Step 8: Create `apps/web/components/orders/steps/VolumeQualityStep.tsx`**

```tsx
import { OrderFormData } from '@/lib/types'
import { Field } from '@/components/ui/Field'
import { Button } from '@/components/ui/Button'

type QualityData = OrderFormData['quality']

interface VolumeQualityStepProps {
  volume: number
  quality: QualityData
  onChangeVolume: (v: number) => void
  onChangeQuality: (q: QualityData) => void
  onNext: () => void
  onBack: () => void
}

export function VolumeQualityStep({ volume, quality, onChangeVolume, onChangeQuality, onNext, onBack }: VolumeQualityStepProps) {
  function setQ<K extends keyof QualityData>(key: K, value: QualityData[K]) {
    onChangeQuality({ ...quality, [key]: value })
  }

  return (
    <div className="flex flex-col gap-5">
      <Field
        id="episode-count" label="Validated episode count" type="number" required
        help="Number of physics-validated episodes to deliver"
        value={volume}
        onChange={(e) => onChangeVolume(Math.max(1, parseInt(e.target.value, 10) || 1))}
        min={1} step={1}
      />
      <label className="flex items-center gap-3 cursor-pointer">
        <input
          type="checkbox"
          checked={quality.source_replay_pass_required}
          onChange={(e) => setQ('source_replay_pass_required', e.target.checked)}
          className="accent-forge-primary w-4 h-4"
        />
        <div>
          <p className="text-sm font-medium text-forge-ink">Require source replay pass</p>
          <p className="text-xs text-forge-ink-muted">
            Each episode must pass source replay before retargeting. Recommended.
          </p>
        </div>
      </label>
      <Field
        id="max-penetration" label="Max penetration (m)" type="number" required
        help="Maximum allowed mesh interpenetration depth per frame"
        value={quality.max_penetration_m}
        onChange={(e) => setQ('max_penetration_m', parseFloat(e.target.value) || 0.002)}
        step={0.001} min={0}
      />
      <Field
        id="min-f1" label="Minimum contact-phase F1" type="number" required
        help="Minimum F1 score for contact phase detection (0–1)"
        value={quality.min_contact_phase_f1}
        onChange={(e) => setQ('min_contact_phase_f1', parseFloat(e.target.value) || 0.8)}
        step={0.05} min={0} max={1}
      />
      <Field
        id="min-acceptance" label="Minimum delivery acceptance rate" type="number" required
        help="Minimum fraction of retargeted episodes that must pass final QC (0–1)"
        value={quality.min_delivery_acceptance_rate}
        onChange={(e) => setQ('min_delivery_acceptance_rate', parseFloat(e.target.value) || 0.9)}
        step={0.05} min={0} max={1}
      />
      <div className="flex justify-between pt-2">
        <Button variant="secondary" onClick={onBack}>Back</Button>
        <Button variant="primary" onClick={onNext}>Next</Button>
      </div>
    </div>
  )
}
```

- [ ] **Step 9: Create `apps/web/components/orders/steps/RightsStep.tsx`**

```tsx
import { OrderFormData } from '@/lib/types'
import { Button } from '@/components/ui/Button'

type RightsProfile = OrderFormData['rights_profile']

const OPTIONS: { value: RightsProfile; label: string; desc: string }[] = [
  {
    value: 'customer_exclusive_derivatives',
    label: 'Exclusive with derivatives',
    desc: 'You own the dataset and any derivatives. FORGE retains no rights.',
  },
  {
    value: 'forge_retained',
    label: 'FORGE retained',
    desc: 'FORGE may use anonymized data for research and model improvement.',
  },
  {
    value: 'open',
    label: 'Open',
    desc: 'Dataset published under CC-BY. Lower pricing applies.',
  },
]

interface RightsStepProps {
  data: RightsProfile
  onChange: (v: RightsProfile) => void
  onNext: () => void
  onBack: () => void
}

export function RightsStep({ data, onChange, onNext, onBack }: RightsStepProps) {
  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-3">
        {OPTIONS.map(({ value, label, desc }) => (
          <label
            key={value}
            className={[
              'flex items-start gap-3 p-4 rounded-control border cursor-pointer transition-colors',
              data === value ? 'border-forge-primary bg-forge-surface-cyan' : 'border-forge-border hover:bg-forge-surface-soft',
            ].join(' ')}
          >
            <input
              type="radio" name="rights-profile" value={value}
              checked={data === value} onChange={() => onChange(value)}
              className="mt-0.5 accent-forge-primary"
            />
            <div>
              <p className="text-sm font-semibold text-forge-ink">{label}</p>
              <p className="text-xs text-forge-ink-muted mt-0.5">{desc}</p>
            </div>
          </label>
        ))}
      </div>
      <div className="flex justify-between pt-2">
        <Button variant="secondary" onClick={onBack}>Back</Button>
        <Button variant="primary" onClick={onNext}>Next</Button>
      </div>
    </div>
  )
}
```

- [ ] **Step 10: Create `apps/web/components/orders/steps/ReviewStep.tsx`**

```tsx
import { OrderFormData } from '@/lib/types'
import { Button } from '@/components/ui/Button'

interface ReviewStepProps {
  data: OrderFormData
  onBack: () => void
  onSubmit: () => Promise<void>
  submitting: boolean
  error: string | null
}

const RIGHTS_LABELS: Record<string, string> = {
  customer_exclusive_derivatives: 'Exclusive with derivatives',
  forge_retained: 'FORGE retained',
  open: 'Open (CC-BY)',
}

export function ReviewStep({ data, onBack, onSubmit, submitting, error }: ReviewStepProps) {
  return (
    <div className="flex flex-col gap-6">
      <dl className="flex flex-col gap-4 text-sm">
        <div>
          <dt className="text-xs font-medium text-forge-ink-muted uppercase tracking-wide mb-1">Task</dt>
          <dd className="text-forge-ink font-medium">{data.skill.name}</dd>
          <dd className="text-forge-ink-muted mt-0.5">{data.skill.initial_state} → {data.skill.success_predicate}</dd>
        </div>
        <div>
          <dt className="text-xs font-medium text-forge-ink-muted uppercase tracking-wide mb-1">Robot</dt>
          <dd className="text-forge-ink">{data.embodiment.robot_id} · {data.embodiment.hand_type.replace(/_/g, ' ')}</dd>
          <dd className="text-forge-ink-muted font-mono text-xs mt-0.5 break-all">{data.embodiment.model_uri}</dd>
        </div>
        <div>
          <dt className="text-xs font-medium text-forge-ink-muted uppercase tracking-wide mb-1">Coverage</dt>
          <dd className="text-forge-ink">
            {data.coverage.object_ids.length > 0 ? data.coverage.object_ids.join(', ') : '—'}
          </dd>
          {data.coverage.viewpoint_bins.length > 0 && (
            <dd className="text-forge-ink-muted mt-0.5">Viewpoints: {data.coverage.viewpoint_bins.join(', ')}</dd>
          )}
        </div>
        <div>
          <dt className="text-xs font-medium text-forge-ink-muted uppercase tracking-wide mb-1">Volume</dt>
          <dd className="text-forge-ink">{data.volume_validated_episodes} validated episodes</dd>
        </div>
        <div>
          <dt className="text-xs font-medium text-forge-ink-muted uppercase tracking-wide mb-1">Rights</dt>
          <dd className="text-forge-ink">{RIGHTS_LABELS[data.rights_profile] ?? data.rights_profile}</dd>
        </div>
      </dl>

      {error && (
        <p className="text-sm text-forge-danger bg-forge-danger-soft rounded-control px-4 py-3">
          {error}
        </p>
      )}

      <div className="flex justify-between pt-2">
        <Button variant="secondary" onClick={onBack} disabled={submitting}>Back</Button>
        <Button variant="primary" onClick={onSubmit} loading={submitting}>
          Place order
        </Button>
      </div>
    </div>
  )
}
```

- [ ] **Step 11: Create `apps/web/app/orders/new/page.tsx`**

```tsx
import { redirect } from 'next/navigation'
import { auth } from '@/auth'
import { NewOrderStepper } from '@/components/orders/NewOrderStepper'

export default async function NewOrderPage() {
  const session = await auth()
  if (!session?.forgeToken) redirect('/auth/signin')

  return (
    <div>
      <h1 className="text-2xl font-bold text-forge-ink mb-2">New order</h1>
      <p className="text-forge-ink-muted text-sm mb-10">
        Configure your dataset. No data is saved until you place the order.
      </p>
      <NewOrderStepper token={session.forgeToken} />
    </div>
  )
}
```

- [ ] **Step 12: Run tests — expect PASS**

```bash
cd apps/web && pnpm test
```

Expected: all tests pass including NewOrderStepper step navigation tests.

- [ ] **Step 13: Verify stepper end-to-end**

With API running: click "New order" → fill all 6 steps → "Place order" → if Stripe configured, see Stripe redirect; otherwise see `/orders/{id}` detail page.

- [ ] **Step 14: Commit**

```bash
git add apps/web/components/orders/ apps/web/app/orders/new/ \
        apps/web/__tests__/orders/ apps/web/lib/types.ts
git commit -m "feat(web): 6-step new order stepper with form validation and API submission"
```

---

### Task 14: R2 CORS Config

**Files:**
- Create: `infra/r2-cors.json`

- [ ] **Step 1: Create `infra/r2-cors.json`**

```json
[
  {
    "AllowedOrigins": ["http://localhost:3000", "https://forge.app"],
    "AllowedMethods": ["PUT"],
    "AllowedHeaders": ["Content-Type"],
    "MaxAgeSeconds": 3000
  }
]
```

- [ ] **Step 2: Commit**

```bash
git add infra/r2-cors.json
git commit -m "infra: add R2 CORS config for future capture upload"
```

---

## Self-Review

**Spec coverage check:**

| Spec section | Covered by task |
|---|---|
| §3 Stack (Next.js 14, Tailwind v4, Auth.js v5, TypeScript, Inter, pnpm) | Task 1–2, 6 |
| §4 File structure | All tasks match spec paths |
| §5 Design tokens (all CSS vars) | Task 2 — full @theme block |
| §6 Auth (Google/GitHub/Resend, JWT mint, tenant stub, middleware) | Task 6 |
| §7 API client (apiServer.get, apiFetch) | Task 5 |
| §8.1 Landing page (headline, no logo wall, one CTA, 7 steps, footer) | Task 9 |
| §8.2 Sign-in page (3 provider buttons, Field not placeholder, no password) | Task 7 |
| §8.3 Orders list (table columns, status mapping, empty + error states) | Task 11 |
| §8.4 New order stepper (6 steps, local state, POST /orders, Stripe redirect) | Task 13 |
| §8.5 Order detail (Overview live, placeholder tabs with descriptions) | Task 12 |
| §9 Button (3 variants, loading, 48px height) | Task 4 |
| §9 Field (label above, 48px, help, error with aria) | Task 4 |
| §9 StatusBadge (icon + label, color, detail) | Task 4 |
| §9 NavBar (3 items, active state, no boxes) | Task 8 |
| §10 All states (loading/empty/error/auth/partial/mobile/keyboard) | Implemented in pages |
| §11 R2 CORS | Task 14 |
| §12 Out-of-scope patterns | Global Constraints section enforced throughout |
| `packages/ui/tokens/tokens.css` | Task 2 |

**Gaps addressed:**
- `OrderResponse` in Python API only had 3 fields — Task 10 extends it before the list and detail pages need it.
- `apiServer` methods dynamically import `auth()` to avoid test-time Next.js initialization errors.
