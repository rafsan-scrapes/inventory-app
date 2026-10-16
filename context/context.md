# Inventory App — Project Overview

## Overview

The Inventory App is a private, login-protected web application for a repair shop's parts warehouse. It tracks spare parts for electronics appliances (refrigerators, washing machines, laptops, and similar) and answers one question in seconds: **what is this part, how many do we have (new and used), and where in the warehouse is it stored?** Each part is classified by Product Type, Brand, and Part Type, carries new/used stock counts, a physical warehouse location (shelf / column / row), model number(s), and an optional photo. Staff can adjust stock on the fly, and any user can export selected parts to a formatted PDF for printing.

The app is **not public** — only the shop's staff use it. There is no customer-facing side and no self-registration; accounts are created manually. The codebase is intentionally structured so more features can be added later.

---

## Goals

1. A staff member can find a part's stock count and warehouse location in under a few seconds using filters and search.
2. Stock counts stay accurate because staff can adjust new/used quantities with one tap, without opening a full edit form.
3. Any signed-in user can export one or more selected parts to a print-ready PDF (5 rows per landscape A4 page) for stocktaking or ordering.

---

## Core User Flow

1. User signs in at `/login/` (Django's built-in auth; no registration).
2. User lands on the Parts Inventory dashboard (`/`) and filters or searches by product type, brand, part type, product model, part model, or stock status.
3. User reads each row: image, product type (+ model), brand, part type, new/used counts, size, part model number, and a colored stock status badge (In Stock / Low In Stock / Out of Stock).
4. Staff clicks **+ / −** on a row to increment or decrement a new/used unit; the count updates in place and a toast confirms the change.
5. Staff clicks **Add Part** to create a new part (creating new product types, brands, or part types inline if needed), or the edit icon to change an existing part.
6. User selects rows with checkboxes, clicks **Export PDF**, and downloads a formatted PDF of the selected parts.
7. User logs out via the Logout button (POST, as required by Django).

---

## Features

### Data Model

The data follows a strict hierarchy:

```
Product Type  (e.g. Washing Machine, Refrigerator, Laptop)   ← independent of Brand
Brand         (e.g. Bosch, LG, Samsung)                       ← independent of Product Type
  └── Part (links Product Type + Brand + Part Type)
        └── Part Model Number (one or more per part)
```

**Key rules:**

- **Product Type** and **Brand** are fully independent — neither cascades from or filters the other.
- A **Part Type** belongs to a Product Type (e.g. "Motor" for Washing Machine) and is unique per `(name, product_type)`.
- A **Part** is the junction of a Product Type, Brand, and Part Type; this triple must be unique.
- A **Part** has new and used stock counts, an optional single image, optional product model, size (free text), a warehouse location (shelf / column / row — must be unique as a triple), and optional notes.
- **Part Model Numbers** are a separate child model — a part can carry any number of them, entered via a tag-style input.
- All three classification FKs (`product_type`, `brand`, `part_type`) are `PROTECT` — you cannot delete a classification still in use.

### Parts Dashboard (Homepage, `/`)

- Full parts table with thumbnail image (click to open a lightbox), product type with product model below it, brand, part type, new/used stock, size, part model number, and a colored stock status badge.
- **Filters (GET form):** Product Type, Brand, Part Type (cascading — populated via AJAX from `/get-part-types/`, respects the selected Product Type), Product Model No. (substring), Part Model No. (substring, also highlights the matched model number in the row), and Stock Status.
- **Stock status summary banners** (persistent): parts that are out of stock (0 total) or low in stock (total ≤ 2) are listed at the top so shortages are visible immediately.
- **Select-all checkbox** and per-row checkboxes for PDF export.
- Staff-only: **Add Part** button, per-row edit icon, and stock adjustment **+ / −** buttons (dimmed at zero).
- No pagination — all parts render in one table.

### Add Part Page (`/add/`)

- Two-column form: **Classification & Image** on the left, **Stock / Location / Details** on the right.
- **Smart dropdowns:** Product Type, Brand, and Part Type each show existing values plus a "＋ Add new type… / ＋ Add new brand…" option that reveals a text input and creates the value on save (`get_or_create`).
- **AJAX cascade:** Part Type is disabled until a Product Type is chosen; choosing one loads only that product type's part types. "＋ Add new type…" is always offered once a product type is selected.
- **Image upload** (optional): JPG/PNG/WebP, click-to-upload area with a live preview.
- **Model No. tag input:** type a value, press Add/Enter, and it becomes a removable tag (duplicates blocked case-insensitively); hidden inputs submit all values.
- **Validation (server-side, via `full_clean()`):**
  - At least one of New Units / Used Units must be greater than zero.
  - The selected Part Type must belong to the selected Product Type.
  - The warehouse location (Shelf + Column + Row) must be unique — the duplicate message is rewritten to a friendly, human-readable one.
- On success: redirects to the dashboard and shows a success toast: `"<part> has been added successfully!"` where `<part>` = `PartType-ProductType-Brand`.

### Edit Part Page (`/part/edit/<id>/`)

- Same layout as Add Part, with all fields pre-filled.
- **Product Type is locked** (shown as text + hidden input) — changing it would orphan the Part Type FK, so it can only be changed by editing through a new part. Brand and Part Type remain editable (part type options are scoped to the locked product type).
- Existing model numbers are pre-rendered as tags; add or remove freely.
- On success: redirects to the dashboard (no toast).

### Stock Adjustment (`/part/<id>/adjust/`)

- AJAX POST endpoint (`field` = `total_new` | `total_used`, `delta` = `+1` | `−1`).
- Counts are floored at 0 server-side (`max(0, current + delta)`).
- While a request is in flight, all adjustment buttons on the page lock; the row updates in place, the page reloads, and a session toast confirms: `"A new part has been added to <part>"` or `"A used part has been removed from <part>"` (types: `add` / `remove`).

### PDF Export (`/export/`)

- POST endpoint that takes the checked `part_id` list (injected into a hidden form by JavaScript) and returns a download via `FileResponse`.
- Built with ReportLab: **landscape A4, 5 rows per page**, 11 columns (`#`, Image, Product Type, Brand, Part Type, New, Used, Size (kg), Model No., Location, Notes), dark-green header bar, alternating row shading, footer with total part count, export timestamp, and page numbers (`Page X of Y`).
- Image column embeds the part photo (83px, centered) when one exists; missing values render as "—".

### Notifications

- **Session toasts** (non-blocking, auto-hide after 3 seconds, colored by type): success (part added), add (stock +1), remove (stock −1), danger (out of stock), warning (low in stock).
- **Persistent banners** on the dashboard listing all out-of-stock / low-in-stock parts.

### Authentication & Roles

| Role | Can do |
|---|---|
| Staff (`is_staff`) | View, search, filter, export, add parts, edit parts, adjust stock |
| Regular user | View, search, filter, export only — Add/Edit/Adjust controls are hidden |
| Superuser | Everything above plus deletion and user management via Django admin (`/admin/`) |

- Every page requires login (`@login_required`); unauthenticated visitors are redirected to `/login/`.
- Deletion happens **only** through Django admin — intentionally, to prevent accidental loss.
- No self-registration; accounts are created manually via `createsuperuser` / admin.

### Pages & Routes

| URL | Name | Purpose |
|---|---|---|
| `/` | `dashboard-index` | Parts table with filters, stock banners, export |
| `/add/` | `add-part` | Add a new part |
| `/part/edit/<pk>` | `edit-part` | Edit an existing part |
| `/part/<pk>/adjust/` | `adjust-stock` | AJAX stock adjustment |
| `/get-part-types/` | `get-part-types` | AJAX cascade: part types by product type |
| `/export/` | `export-pdf` | PDF export (POST) |
| `/login/` | `user-login` | Login page |
| `/logout/` | `user-logout` | Logout (POST) |
| `/admin/` | — | Django admin |

### Field Rules

| Field | Required | Type | Notes |
|---|---|---|---|
| Product Type | Yes | FK (create-or-select) | Independent of Brand |
| Brand | Yes | FK (create-or-select) | Independent of Product Type |
| Part Type | Yes | FK (create-or-select) | Cascades from Product Type; must belong to it |
| Product Model | No | Free text CharField | e.g. "RS70F65Q1BLV" |
| Image | No | ImageField (single) | JPG, PNG, WebP; preview before upload |
| New Units | Yes | PositiveInteger | At least one of New/Used must be > 0 |
| Used Units | Yes | PositiveInteger | Same rule as New Units |
| Size | No | Free text CharField | Any unit, e.g. "5.5kg/9kg" |
| Model No. | No | Multiple CharFields | Tag input; any number of values |
| Shelf / Column / Row | Yes | Free text CharFields | Combined triple must be unique |
| Notes | No | TextField | Optional remarks (condition, origin, etc.) |

Size, shelf, column, and row are deliberately free-text — nothing is validated as a specific number or format.

---

## Scope

### In Scope

- Parts catalog classified by Product Type, Brand, and Part Type, with one image, model number(s), size, and notes per part.
- New/used stock counts with quick AJAX adjustment and a 0-floor.
- Warehouse location tracking (shelf / column / row) with uniqueness enforcement.
- Dashboard with filtering, substring search (product model & part model), and stock status.
- Stock status derivation (In Stock / Low In Stock ≤ 2 / Out of Stock 0) and shortage banners.
- PDF export of selected parts via ReportLab.
- Staff vs. read-only roles; login required; deletion only via Django admin.
- Session toast notifications for add/adjust actions.

### Out of Scope

- Customer-facing catalog or public access of any kind.
- Deletion inside the app UI (recycle bin / soft delete).
- Multiple images per part, image carousels, or drag-and-drop upload.
- Barcode/QR scanning, CSV/Excel import or export, and stock movement history.
- Automated low-stock alerts (email/SMS) and restock lists.
- A separate mobile app.

This section is expected to grow — new features should be added to **Features** and mirrored in **Scope** as they are built.

---

## Success Criteria

1. A signed-in staff user can add a part in one form, creating a new Product Type, Brand, and Part Type inline without leaving the page, and the new part appears in the dashboard with a success toast.
2. Selecting a Product Type in any cascade updates the Part Type options to only that product type's part types, both on the dashboard filter and the add form.
3. A staff user can increment and decrement new/used stock by one from the dashboard; values persist, never drop below zero, and a toast confirms each change.
4. Filtering by product model or part model substring returns the correct parts, and a part model search highlights the matched model number in the table.
5. Selecting one or more parts and clicking Export PDF downloads a landscape A4 PDF with an image column, location, stock counts, page numbers, and an export timestamp.
6. A regular (non-staff) user can view, search, and export, but sees no Add, Edit, or stock adjustment controls.
7. Adding a part with a duplicate warehouse location (shelf/column/row) shows a clear, friendly validation error instead of a technical one.

---

## Tech Stack

- **Backend:** Django 6 (Python 3.13), SQLite3
- **Frontend:** Server-rendered Django templates, vanilla JavaScript (fetch/AJAX), custom `style.css`, Font Awesome icons (CDN)
- **Font:** Poppins (Google Fonts)
- **PDF:** ReportLab
- **Images:** Django `ImageField` (Pillow); served from `/media/`
- **Static:** WhiteNoise (`CompressedManifestStaticFilesStorage`), `STATIC_ROOT` = `asert/`
- **Auth:** Django built-in `django.contrib.auth`
- **Deployment:** Namecheap Stellar shared hosting via `passenger_wsgi.py`

## Design

- **Palette (CSS custom properties, oklch):** light green-tinted neutrals for the page background, dark teal primary for buttons and accents, with success/warning/danger colors for stock states.
- **Typography:** Poppins, 14px base, with rounded buttons (6px) and cards.
- **Layout:** Single-column form pages on mobile, two-column add/edit grid on desktop; the dashboard is a dense, responsive table that stays usable on small screens.
- **Interactions:** image lightbox, smart "add new" dropdowns, tag-style model-number input, toast notifications.
