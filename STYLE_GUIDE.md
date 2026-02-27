# Cloze Style Guide

Design system and UI conventions for the Cloze application.

---

## Design Tokens

Custom colors defined in `tailwind.config` (inside `templates/base.html`):

| Token | Hex | Usage |
|---|---|---|
| `page` | `#FAF9F7` | Page background (warm off-white) |
| `surface` | `#FFFFFF` | Card / container backgrounds |
| `muted` | `#F5F4F0` | Subtle surfaces — AI chat bubbles, footers, code blocks |
| `cloze-indigo` | `#5B5FC7` | Primary brand — buttons, active states, links, stat numbers |
| `cloze-sky` | `#7DBBDA` | User chat avatar |
| `cloze-hover` | `#4E51B0` | Hover state for primary indigo |
| `cloze-lavender` | `#EEEAF6` | Active nav background, patient/provider login page background |

Standard Tailwind palettes used alongside these: `stone-*` (warm neutrals), `violet-*` (sidebar/accents), `amber-*` (warnings/scheduled), `emerald-*` (success/active), `red-*` (errors/danger), `indigo-*` (processing states).

**Key principle:** Warm `stone-*` neutrals throughout — never `slate-*` or `gray-*`.

---

## Layout

### Authenticated pages

Two-column layout: fixed 256px sidebar + flexible main column.

```
┌──────────┬────────────────────────────────┐
│          │  Top bar (h-14, sticky)        │
│ Sidebar  ├────────────────────────────────┤
│ (w-64)   │                                │
│          │  Main content (p-6)            │
│          │                                │
└──────────┴────────────────────────────────┘
```

- Body: `min-h-screen bg-page text-stone-900 antialiased`
- Main content: `<main class="w-full flex-1 p-6">`
- Full-height pages (chat): `h-screen overflow-hidden` on body

### Login pages

Centered card, no sidebar. Two variants:

- **Patient/provider:** `bg-[#EEEAF6]` (lavender) background, white card
- **Admin:** `background:#1c1926` (dark with subtle indigo-purple tint), dark card

---

## Sidebar

```
bg-[#F8F6FC]          ← lavender tint background
border-r border-violet-100  ← right border
```

- **Section labels:** `text-[11px] font-semibold uppercase tracking-wider text-stone-400`
- **Nav items (default):** `rounded-lg px-3 py-2 text-sm text-stone-600 hover:bg-violet-50`
- **Nav items (active):** `bg-cloze-lavender text-cloze-indigo font-medium` (applied by JS in `shared.js`)
- **Nav icons:** `h-[18px] w-[18px] text-stone-400` → active: `text-cloze-indigo`
- **Footer divider:** `border-t border-violet-100`

---

## Top Bar

```html
<header class="sticky top-0 z-20 flex h-14 items-center gap-3
               border-b border-stone-200 bg-white/90 px-4 backdrop-blur-sm">
```

- Page title: `text-[15px] font-semibold text-stone-900`
- Frosted glass effect via `bg-white/90 backdrop-blur-sm`

---

## Buttons

### Primary

```
rounded-md bg-cloze-indigo px-4 py-2 text-sm font-medium text-white
transition hover:bg-cloze-hover
```

Size variants: `px-3 py-1.5 text-xs` (small) · `px-4 py-2 text-sm` (default) · `px-5 py-2.5 text-sm font-semibold` (large)

Disabled: add `disabled:opacity-50 disabled:cursor-not-allowed`

### Secondary / outline

```
rounded-md border border-stone-200 px-4 py-2 text-sm font-medium text-stone-600
transition hover:bg-stone-50
```

### Tertiary / ghost

```
rounded-md bg-stone-100 px-4 py-2 font-medium text-stone-700 hover:bg-stone-200
```

### Danger

```
text-xs font-medium text-red-600 transition hover:text-red-700
```

Or as a button: `rounded-md border border-stone-200 px-2 py-1 text-sm hover:bg-stone-100 text-rose-600`

### Subtle indigo tint (e.g. "View Plan")

```
rounded-md border border-cloze-indigo/30 bg-cloze-indigo/5 px-3 py-1
text-xs font-medium text-cloze-indigo transition hover:bg-cloze-indigo/10
```

### Success / add

```
rounded-md bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-700
```

---

## Cards & Containers

### Standard card

```
rounded-lg border border-stone-200 bg-white
```

**Rules:** No `rounded-xl`. No `shadow-*` on static containers. No gradients.

Shadows are only used on: modals (`shadow-lg`), hover-lift cards (`hover:shadow-md`), and slide-in drawers (`shadow-xl`).

### Card with section header

```html
<section class="rounded-lg border border-stone-200 bg-white overflow-hidden">
  <div class="border-b border-stone-100 px-5 py-3">
    <h3 class="text-sm font-semibold text-stone-900">Title</h3>
  </div>
  <div class="px-5 py-4">…</div>
</section>
```

### Stat card

```
rounded-lg border border-violet-100 bg-violet-50/40 px-4 py-4
```

Number: `text-2xl font-semibold text-cloze-indigo`
Label: `mt-0.5 text-xs text-stone-500`

### Empty state (dashed border)

```
rounded-lg border border-dashed border-stone-200 bg-white p-6 text-center text-sm text-stone-600
```

---

## Tables

```html
<div class="overflow-hidden rounded-lg border border-stone-200 bg-white">
  <table class="w-full text-sm">
    <thead>
      <tr class="border-b border-stone-100 bg-violet-50/60 text-left">
        <th class="px-4 py-3 font-semibold text-stone-700">…</th>
      </tr>
    </thead>
    <tbody class="divide-y divide-stone-100">
      <tr class="cursor-pointer transition hover:bg-violet-50/40">
        <td class="px-4 py-3 font-medium text-stone-900">…</td>
        <td class="px-4 py-3 text-stone-600">…</td>
      </tr>
    </tbody>
  </table>
</div>
```

- Header background: `bg-violet-50/60`
- Row hover: `hover:bg-violet-50/40`
- Dividers: `divide-y divide-stone-100`

---

## Form Inputs

### Text input (light theme)

```
w-full rounded-md border border-stone-300 bg-white px-3 py-2
text-sm text-stone-900 outline-none transition
placeholder:text-stone-400
focus:border-cloze-indigo focus:ring-1 focus:ring-cloze-indigo
```

### Text input (dark theme — admin login)

```
w-full rounded-md border border-stone-600 bg-stone-700 px-3 py-2
text-sm text-white outline-none transition
placeholder:text-stone-500
focus:border-cloze-indigo focus:ring-1 focus:ring-cloze-indigo
```

### Search input with icon

Icon positioned `absolute left-3 top-1/2 -translate-y-1/2`, input uses `pl-10`.

### Textarea

```
w-full resize-y rounded-md border-2 border-stone-200 px-3 py-2 text-sm
outline-none focus:border-cloze-indigo
```

Note: form modals use `border-2` (2px). Inline search inputs use `border` (1px).

### Label

```
mb-1.5 block text-sm font-medium text-stone-700
```

### Checkbox

```
accent-cloze-indigo h-4 w-4
```

### Select

```
w-full rounded-md border border-stone-300 px-3 py-2 text-sm
focus:border-cloze-indigo focus:outline-none focus:ring-1 focus:ring-cloze-indigo
```

---

## Badges & Status Pills

All badges: `inline-flex rounded-full px-2.5 py-0.5 text-sm font-medium` with `ring-1 ring-inset`.

| State | Classes |
|---|---|
| Active / success | `bg-emerald-50 text-emerald-700 ring-emerald-200` |
| Scheduled / pending | `bg-amber-50 text-amber-700 ring-amber-200` |
| Processing | `bg-indigo-50 text-indigo-700 ring-indigo-200` |
| Complete / ready | `bg-violet-50 text-violet-700 ring-violet-200` |
| Draft / neutral | `bg-stone-100 text-stone-600 ring-stone-200` |
| Error / missing | `bg-red-50 text-red-600 ring-red-200` |

### Role badges

| Role | Classes |
|---|---|
| Admin | `bg-red-50 text-red-700 ring-red-200` |
| Provider | `bg-emerald-50 text-emerald-700 ring-emerald-200` |
| Patient | `bg-blue-50 text-blue-700 ring-blue-200` |

### Small badges (11px)

For tighter contexts: `rounded-full px-2 py-0.5 text-[11px] font-semibold`

### Indigo pill (tags, model names)

```
inline-flex rounded-full bg-cloze-indigo/10 px-2.5 py-0.5 text-xs font-semibold text-cloze-indigo
```

---

## Modals

### Standard modal

```html
<div class="fixed inset-0 z-50 hidden items-center justify-center bg-black/40">
  <div class="w-full max-w-md rounded-lg bg-white p-6 shadow-lg">
    <h3 class="mb-5 text-base font-semibold text-stone-900">Title</h3>
    <!-- content -->
    <div class="flex items-center justify-end gap-3">
      <button class="…secondary…">Cancel</button>
      <button class="…primary…">Confirm</button>
    </div>
  </div>
</div>
```

- Backdrop: `bg-black/40`
- Panel: `rounded-lg bg-white p-6 shadow-lg`
- Toggle: JS removes `hidden` + adds `flex` to show

### Full-screen modal (reports)

Uses `absolute inset-4 sm:inset-8 md:inset-12 lg:inset-16` for responsive inset sizing.

### Close button

```
rounded-md p-1 text-stone-400 transition hover:text-stone-700
```

---

## Tabs

### Underline tabs (horizontal)

```html
<!-- Active -->
<button class="relative -mb-px border-b-2 border-cloze-indigo
               px-2 py-3 text-sm font-medium text-stone-900">

<!-- Inactive -->
<button class="relative -mb-px border-b-2 border-transparent
               px-2 py-3 text-sm font-medium text-stone-600 hover:text-stone-900">
```

### Sidebar-driven tabs (admin dashboard)

Tabs mapped to URL hash fragments (`#overview`, `#patients`, etc.). Sidebar links drive `switchTab()` via `hashchange` event.

---

## Alerts & Banners

### Warning callout (amber)

```
rounded-lg border border-amber-200 bg-amber-50 p-5
```

With left border: `rounded-lg border-l-4 border-amber-400 bg-amber-50 p-4`

### Error callout (red)

Left border variant: `rounded-lg border-l-4 border-red-500 bg-red-50 p-4`

### Error message (inline, in forms)

Light: `rounded-md bg-red-50 px-3 py-2.5 text-sm text-red-700 ring-1 ring-inset ring-red-200`
Dark: `rounded-md bg-red-900/40 px-3 py-2.5 text-sm text-red-300 ring-1 ring-inset ring-red-800`

### Info tint (indigo)

```
rounded-md bg-cloze-indigo/10 px-3 py-2 text-sm text-cloze-indigo
```

---

## Typography

| Element | Classes |
|---|---|
| Page heading (H1) | `text-xl font-semibold text-stone-900` |
| Section heading (H2) | `text-lg font-semibold text-stone-900` |
| Card heading (H3) | `text-sm font-semibold text-stone-900` |
| Uppercase label | `text-[11px] font-semibold uppercase tracking-wider text-stone-400` |
| Body text | `text-sm text-stone-600` or `text-sm text-stone-700` |
| Caption | `text-xs text-stone-500` |
| Timestamp | `text-xs text-stone-400` or `text-[11px] text-stone-400` |
| Stat number | `text-2xl font-semibold text-cloze-indigo` |
| Link | `text-sm font-medium text-cloze-indigo hover:text-cloze-hover` |
| Destructive link | `text-xs font-medium text-red-600 hover:text-red-700` |

---

## Icons

All icons are **inline SVGs** — no icon library, no emojis anywhere in the UI.

| Context | Size | Stroke width |
|---|---|---|
| Sidebar nav | `h-[18px] w-[18px]` | `1.7` |
| Buttons / table actions | `h-4 w-4` | `2` |
| Modal close / larger actions | `h-5 w-5` | `1.8` |
| Small inline (badges) | `h-3.5 w-3.5` | `2` |

All use `fill="none" stroke="currentColor"` and inherit color from `text-*` classes via `currentColor`.

---

## Chat Bubbles

```
┌──────┬────────────────────────────────┐
│ Avatar│  Message bubble               │
│ 36px  │  rounded-lg px-4 py-3        │
│ rounded│ text-sm leading-relaxed      │
└──────┴────────────────────────────────┘
```

| Element | User | AI |
|---|---|---|
| Avatar bg | `bg-cloze-sky` (#7DBBDA) | `bg-stone-600` or `bg-[#312E81]` |
| Bubble bg | `bg-cloze-indigo/5` | `bg-muted` (#F5F4F0) |

- Avatar: `h-9 w-9 rounded-lg` with centered initial letter
- Message entry: `fadeIn 0.3s ease-in` animation (translateY 10px → 0)

---

## Spacing Conventions

| Context | Value |
|---|---|
| Page content padding | `p-6` |
| Card inner padding | `px-5 py-4` (body), `px-5 py-3` (header) |
| Modal padding | `p-6` |
| Table cell padding | `px-4 py-3` |
| Section gaps | `mb-6` or `mb-8` |
| Grid item gaps | `gap-3` or `gap-4` |
| Form field spacing | `space-y-4` or `space-y-5` |
| Nav item spacing | `space-y-0.5` |
| List dividers | `divide-y divide-stone-100` |

---

## Z-index Layers

| z-index | Element |
|---|---|
| `z-20` | Top bar |
| `z-30` | Mobile overlay |
| `z-40` | Sidebar, drawers |
| `z-50` | Standard modals |
| `z-[1000]` | Context menus, report modals |
| `z-[2000]` | Safety disclaimer modal (highest) |

---

## Key Principles

1. **Warm neutrals** — `stone-*` palette, never `slate-*` or `gray-*`
2. **Violet accents** — sidebar, table headers, hover states use `violet-50/60` tones
3. **No decorative shadows** — shadows only on modals, drawers, and interactive hover-lift cards
4. **No rounded-xl** — `rounded-lg` maximum on containers, `rounded-md` on inputs/buttons
5. **No gradients** — flat colors throughout
6. **No emojis** — inline SVGs for all iconography
7. **Ring-inset badges** — all status pills use `ring-1 ring-inset` instead of solid borders
8. **Indigo as primary** — `cloze-indigo` for all primary actions, active states, and brand accents
9. **Lavender as ambient** — `cloze-lavender` / `violet-50` for backgrounds and soft highlights
