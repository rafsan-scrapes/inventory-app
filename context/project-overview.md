# Inventory App — Project Overview

## Overview

The Inventory App is a private, login-protected web application for a repair shop's parts warehouse. It tracks spare parts for electronics appliances (refrigerators, washing machines, laptops, and similar) and answers one question in seconds: **what is this part, how many do we have (new and used), how many are stored in the warehouse vs. in a technician's car, and where in the warehouse or in which car is it stored?** Each part is classified by Product Type, Brand, and Part Type, carries new/used stock counts split across warehouse and car locations, a physical warehouse location (shelf / column / row), model number(s), and an optional photo. Staff can adjust stock on the fly for both the warehouse and any technician car, and any user can export selected parts to a formatted PDF for printing.

The app is **not public** — only the shop's staff use it. There is no customer-facing side and no self-registration; accounts are created manually. The codebase is intentionally structured so more features can be added later.

---

## Goals

1. A staff member can find a part's stock count and warehouse location in under a few seconds using filters and search.
2. Stock counts stay accurate because staff can adjust new/used quantities for the warehouse and for individual cars with one tap, without opening a full edit form.
3. Staff can record and track which technician cars carry which parts (by license plate), how many of each condition (new/used), and adjust those counts — with a confirmation modal that handles both standalone adjustments and warehouse ↔ car transfers.
4. Any signed-in user can export one or more selected parts to a print-ready PDF (5 rows per landscape A4 page) that includes both warehouse and car stock breakdowns.

---

## Core User Flow

1. User signs in at `/login/` (Django's built-in auth; no registration).
2. User lands on the Parts Inventory dashboard (`/`) and filters or searches by product type, brand, part type, product model, part model, stock status, or **storage location** (All / Warehouse Only / a specific car by license plate).
3. User reads each row: image, product type (+ model), brand, part type, new/used totals (warehouse + all cars combined), size, part model number, a colored stock status badge (In Stock / Low In Stock / Out of Stock), and an expandable **Car Stock** sub-row.
4. User expands the Car Stock sub-row on any row to see a breakdown table: warehouse count (new/used) and one entry per car carrying that part (license plate, new count, used count).
5. Staff clicks **+ / −** on the warehouse row or on a car row to adjust counts. A confirmation modal appears asking whether this is a standalone add/remove or a warehouse ↔ car transfer, then applies the change atomically.
6. Staff clicks **Add Part** to create a new part (creating new product types, brands, or part types inline if needed), or the edit icon to change an existing part. The Add/Edit form optionally allows setting initial car stock.
7. User selects rows with checkboxes, clicks **Export PDF**, and downloads a formatted PDF of the selected parts including car stock breakdown.
8. User logs out via the Logout button (POST, as required by Django).

---

## Features

### Data Model

The data follows a strict hierarchy:

```
Product Type  (e.g. Washing Machine, Refrigerator, Laptop)   ← independent of Brand
Brand         (e.g. Bosch, LG, Samsung)                       ← independent of Product Type
  └── Part (links Product Type + Brand + Part Type)
        ├── Part Model Number (one or more per part)
        └── CarStock (one row per part × license plate × condition)
```

**Key rules:**

- **Product Type** and **Brand** are fully independent — neither cascades from or filters the other.
- A **Part Type** belongs to a Product Type (e.g. "Motor" for Washing Machine) and is unique per `(name, product_type)`.
- A **Part** is the junction of a Product Type, Brand, and Part Type; this triple must be unique.
- A **Part** has new and used **warehouse** stock counts (`total_new`, `total_used`), an optional single image, optional product model, size (free text), a warehouse location (shelf / column / row — must be unique as a triple), and optional notes.
- **Part Model Numbers** are a separate child model — a part can carry any number of them, entered via a tag-style input.
- **CarStock** is a child model of Part: `(part FK, license_plate CharField, condition ["new"|"used"], quantity PositiveIntegerField)`. The triple `(part, license_plate, condition)` is unique. Quantity is floored at 0.
- Cars are not a first-class model — they are identified solely by their license plate string on `CarStock` rows. The set of known license plates is derived from existing `CarStock` records.
- All three classification FKs (`product_type`, `brand`, `part_type`) are `PROTECT` — you cannot delete a classification still in use.

### Stock Count Semantics

- `Part.total_new` and `Part.total_used` represent **warehouse** counts only.
- Dashboard "New" and "Used" display columns show **combined totals**: warehouse + sum of all `CarStock` rows for that part and condition.
- The stock status badge (In Stock / Low In Stock / Out of Stock) is derived from the **combined total** (new + used across warehouse and all cars).
- Low In Stock threshold: combined total ≤ 2.
- Out of Stock: combined total = 0.

### Parts Dashboard (Homepage, `/`)

- Full parts table with thumbnail image (click to open a lightbox), product type with product model below it, brand, part type, combined new/used stock, size, part model number, stock status badge, and a Car Stock expander.
- **Car Stock sub-row (collapsible):** clicking the expander on a row reveals a nested breakdown table:
  - One row for the warehouse: new count, used count, warehouse location.
  - One row per `(license_plate, condition)` CarStock record: license plate, condition, quantity, with staff +/− buttons.
  - If no car stock exists for a part, the sub-row shows "Not in any car."
- **Filters (GET form):** Product Type, Brand, Part Type (cascading — populated via AJAX from `/get-part-types/`), Product Model No. (substring), Part Model No. (substring, highlights matched model), Stock Status, and **Storage Location** (`All` / `Warehouse Only` / individual car license plates derived from existing CarStock records).
- **Stock status summary banners** (persistent): parts that are out of stock or low in stock (combined total) are listed at the top.
- **Select-all checkbox** and per-row checkboxes for PDF export.
- Staff-only: **Add Part** button, per-row edit icon, and stock adjustment **+ / −** buttons for both warehouse and car rows.
- No pagination — all parts render in one table.

### Stock Adjustment — Warehouse (existing, updated)

- AJAX POST to `/part/<id>/adjust/` (`field` = `total_new` | `total_used`, `delta` = `+1` | `−1`).
- Before the AJAX call fires, a **confirmation modal** appears:

  **When adding to warehouse (+1):**
  > "Is this a new part arriving at the warehouse, or is it being transferred from a car?"
  > Options: **Standalone add** | **Transfer from car** (shows license plate selector of cars carrying this part)

  **When removing from warehouse (−1):**
  > "Is this part being used/discarded, or is it being transferred to a car?"
  > Options: **Standalone remove** | **Transfer to car** (shows license plate selector; creates a new CarStock row if the car doesn't already carry this part for that condition)

- If **Transfer** is chosen, the endpoint adjusts both `Part.total_new/used` (warehouse) and the corresponding `CarStock.quantity` atomically (database transaction).
- Counts are floored at 0 server-side.

### Stock Adjustment — Car Stock (new)

- AJAX POST to `/part/<id>/adjust-car/` (`license_plate`, `condition` = `new` | `used`, `delta` = `+1` | `−1`).
- Before the AJAX call fires, a **confirmation modal** appears:

  **When adding to car (+1):**
  > "Is this a new part going directly into the car, or is it being transferred from the warehouse?"
  > Options: **Standalone add** | **Transfer from warehouse** (subtracts 1 from `Part.total_new/used` atomically)

  **When removing from car (−1):**
  > "Is this part being used/installed (consumed), or is it being transferred to the warehouse?"
  > Options: **Part used/installed** (standalone remove — no corresponding add) | **Transfer to warehouse** (adds 1 to `Part.total_new/used` atomically)

- `CarStock.quantity` is floored at 0. If it reaches 0, the `CarStock` row is **deleted** (not left at zero), so license plates with no stock disappear cleanly.
- All warehouse ↔ car transfers execute inside a single database transaction.
- A session toast confirms each change.

### Add Part Page (`/add/`)

- Two-column form: **Classification & Image** on the left, **Stock / Location / Details** on the right.
- **Smart dropdowns:** Product Type, Brand, and Part Type each show existing values plus a "＋ Add new…" option that reveals a text input and creates the value on save (`get_or_create`).
- **AJAX cascade:** Part Type is disabled until a Product Type is chosen.
- **Image upload** (optional): JPG/PNG/WebP, click-to-upload area with a live preview.
- **Model No. tag input:** type a value, press Add/Enter, it becomes a removable tag; hidden inputs submit all values.
- **Car Stock section (optional):** staff can add one or more initial car stock entries inline — each entry takes a license plate (free text), condition (new/used), and quantity. Entries can be added/removed with + / − row buttons before saving. If left empty, no `CarStock` rows are created.
- **Validation (server-side, via `full_clean()`):**
  - At least one of warehouse New Units / warehouse Used Units / any car stock quantity must be greater than zero.
  - The selected Part Type must belong to the selected Product Type.
  - The warehouse location (Shelf + Column + Row) must be unique — friendly error message.
  - Each `(license_plate, condition)` pair in the car stock section must be unique within the form.
- On success: redirects to dashboard with toast: `"<part> has been added successfully!"`.

### Edit Part Page (`/part/edit/<id>/`)

- Same layout as Add Part, with all fields pre-filled.
- **Product Type is locked** (shown as text + hidden input).
- Existing car stock entries are pre-rendered as editable rows (license plate, condition, quantity). Staff can modify quantities, add new car entries, or remove existing ones.
- Removing a car entry in the edit form deletes the corresponding `CarStock` row on save.
- On success: redirects to dashboard (no toast).

### PDF Export (`/export/`)

- POST endpoint taking checked `part_id` list; returns a download via `FileResponse`.
- Built with ReportLab: **landscape A4, 5 rows per page**, columns: `#`, Image, Product Type, Brand, Part Type, Warehouse New, Warehouse Used, Car Stock (summarised as `qty-condition-plate` entries, one per line), Size (kg), Model No., Location, Notes.
- Dark-green header bar, alternating row shading, footer with total part count, export timestamp, and page numbers (`Page X of Y`).
- Car Stock column: if no car stock, renders "—"; otherwise lists each `CarStock` record as `{qty}-{condition}-{plate}`, newline-separated.

### Notifications

- **Session toasts** (non-blocking, auto-hide after 3 seconds): success (part added), add (stock +1), remove (stock −1), transfer (warehouse ↔ car), danger (out of stock), warning (low in stock).
- **Persistent banners** on the dashboard listing all out-of-stock / low-in-stock parts (combined total).

### Authentication & Roles

| Role | Can do |
|---|---|
| Staff (`is_staff`) | View, search, filter, export, add parts, edit parts, adjust warehouse stock, adjust car stock |
| Regular user | View, search, filter, export only — Add/Edit/Adjust controls are hidden |
| Superuser | Everything above plus deletion and user management via Django admin (`/admin/`) |

- Every page requires login (`@login_required`).
- Deletion (of Parts, CarStock, classifications) happens **only** through Django admin.
- No self-registration.

### Pages & Routes

| URL | Name | Purpose |
|---|---|---|
| `/` | `dashboard-index` | Parts table with filters, stock banners, export |
| `/add/` | `add-part` | Add a new part |
| `/part/edit/<pk>` | `edit-part` | Edit an existing part |
| `/part/<pk>/adjust/` | `adjust-stock` | AJAX warehouse stock adjustment (with modal) |
| `/part/<pk>/adjust-car/` | `adjust-car-stock` | AJAX car stock adjustment (with modal) |
| `/get-part-types/` | `get-part-types` | AJAX cascade: part types by product type |
| `/get-car-plates/` | `get-car-plates` | AJAX: license plates carrying a given part (for transfer modal) |
| `/export/` | `export-pdf` | PDF export (POST) |
| `/login/` | `user-login` | Login page |
| `/logout/` | `user-logout` | Logout (POST) |
| `/admin/` | — | Django admin |

### Field Rules

| Field | Required | Type | Notes |
|---|---|---|---|
| Product Type | Yes | FK (create-or-select) | Independent of Brand |
| Brand | Yes | FK (create-or-select) | Independent of Product Type |
| Part Type | Yes | FK (create-or-select) | Cascades from Product Type |
| Product Model | No | Free text CharField | e.g. "RS70F65Q1BLV" |
| Image | No | ImageField (single) | JPG, PNG, WebP |
| New Units (warehouse) | Yes* | PositiveInteger | *At least one stock source must be > 0 |
| Used Units (warehouse) | Yes* | PositiveInteger | Same rule |
| Size | No | Free text CharField | Any unit |
| Model No. | No | Multiple CharFields | Tag input |
| Shelf / Column / Row | Yes | Free text CharFields | Combined triple must be unique |
| Notes | No | TextField | Optional |
| Car Stock entries | No | `CarStock` child rows | License plate + condition + quantity; optional at create/edit time |

**CarStock fields:**

| Field | Required | Type | Notes |
|---|---|---|---|
| Part | Yes | FK → Part (CASCADE) | |
| License Plate | Yes | CharField | Free text; no format validation |
| Condition | Yes | CharField choices | `"new"` or `"used"` |
| Quantity | Yes | PositiveIntegerField | ≥ 0; row deleted when it reaches 0 via adjustment |

---

## Scope

### In Scope

- Parts catalog classified by Product Type, Brand, and Part Type, with one image, model number(s), size, and notes per part.
- Warehouse new/used stock counts with quick AJAX adjustment, 0-floor, and confirmation modal (standalone vs. transfer).
- Car stock tracking via `CarStock` (license plate × condition × quantity) with quick AJAX adjustment and confirmation modal (standalone / transfer / used-installed).
- Collapsible car stock sub-row on the dashboard showing per-car breakdown.
- Combined stock totals (warehouse + all cars) shown in dashboard columns and used for stock status badge and shortage banners.
- Storage Location filter: All / Warehouse Only / individual car by license plate.
- Dashboard with filtering, substring search, and stock status.
- PDF export of selected parts including car stock breakdown.
- Staff vs. read-only roles; login required; deletion only via Django admin.
- Session toast notifications for add/adjust/transfer actions.

### Out of Scope

- Cars as a first-class model (driver names, make/model, etc.) — license plate only.
- Per-car shortage banners or alerts.
- Stock movement history / audit log.
- Customer-facing catalog or public access.
- Deletion inside the app UI.
- Multiple images per part.
- Barcode/QR scanning, CSV/Excel import or export.
- Automated low-stock alerts (email/SMS).
- A separate mobile app.

---

## Success Criteria

1. A signed-in staff user can add a part in one form, optionally assigning initial car stock, and the new part appears in the dashboard with correct combined totals.
2. The dashboard "New" and "Used" columns show combined warehouse + car totals; the stock status badge reflects the combined total.
3. Expanding the Car Stock sub-row on any part row shows a breakdown table: warehouse (new/used) and one row per car carrying that part.
4. A staff user can increment and decrement warehouse stock; the confirmation modal appears and correctly handles both standalone adjustments and warehouse-to-car / car-to-warehouse transfers atomically.
5. A staff user can increment and decrement car stock; the modal correctly handles standalone add, standalone remove (part consumed), and car-to-warehouse / warehouse-to-car transfers atomically.
6. The Storage Location filter returns only parts present in the selected location (warehouse or a specific car).
7. Selecting one or more parts and clicking Export PDF downloads a landscape A4 PDF that includes a Car Stock column summarising per-car quantities.
8. A regular (non-staff) user sees no Add, Edit, or stock adjustment controls but can view expanded car stock sub-rows and use all filters including Storage Location.
9. When a CarStock quantity reaches 0 via AJAX adjustment, the row is deleted and the car's license plate disappears from the sub-row and the Storage Location filter.

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
- **Interactions:** image lightbox, smart "add new" dropdowns, tag-style model-number input, toast notifications, collapsible car stock sub-rows, confirmation modal for stock adjustments.
- **Modal design:** lightweight overlay modal (no external library), keyboard-dismissible (Escape), focus-trapped for accessibility.