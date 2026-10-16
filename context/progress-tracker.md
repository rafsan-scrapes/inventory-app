# Progress Tracker — Car Stock Feature

Update this file after every meaningful implementation change.

---

## Current Phase

In Progress

## Current Goal

Add car stock tracking to the Inventory App: a `CarStock` child model, collapsible sub-rows on the dashboard, a confirmation modal for warehouse and car stock adjustments (standalone vs. transfer vs. consumed), a Storage Location filter, and updated PDF export with car stock breakdown.

---

## Completed

- **Unit 1 — `CarStock` model + migration + admin inline (2026-08-02):**
  - Added `CarStock` to `dashboard/models.py`: `part` FK → `Part` (CASCADE, `related_name="carstock_set"`), `license_plate` CharField(50), `condition` choices [new/used], `quantity` PositiveIntegerField(default=1); `unique_together (part, license_plate, condition)`; verbose names "Car Stock Entry"/"Car Stock Entries".
  - Registered `CarStockInline` (pattern of `PartModelNumberInline`) in `PartAdmin.inlines` in `dashboard/admin.py`.
  - Migration `dashboard/0005_carstock` created and applied cleanly (`migrate` OK). `manage.py check` — no issues. Admin inline registration confirmed via shell.

## In Progress

- (none — Unit 1 complete; next is Unit 2: combined stock totals on `Part`)


---

## Next Up

Work through these units in order. Do not skip ahead. Each unit must work end-to-end before the next begins.

### Unit 1 — `CarStock` model + migration
- Define `CarStock(part FK→Part CASCADE, license_plate CharField, condition choices[new/used], quantity PositiveIntegerField)`.
- Unique constraint on `(part, license_plate, condition)`.
- `quantity` minimum is 0 (enforced server-side; row is deleted when it hits 0 via adjustment, not here in the model).
- Write and run the migration.
- Register `CarStock` in Django admin (inline under Part).
- **Verify:** `python manage.py migrate` completes cleanly; CarStock is visible in `/admin/`.

### Unit 2 — Combined stock totals on `Part`
- Add a `combined_new` and `combined_used` property (or annotation) to `Part` that returns `total_new + sum(CarStock[condition=new])` and `total_used + sum(CarStock[condition=used])`.
- Update the dashboard queryset to annotate or prefetch CarStock so combined totals can be computed without N+1 queries.
- Update the stock status badge logic to use combined totals.
- Update the out-of-stock / low-in-stock banner queryset to use combined totals.
- **Verify:** create a test part with warehouse stock only → badge is correct. Add a CarStock row via admin → combined total and badge update correctly on dashboard.

### Unit 3 — Car Stock sub-row (collapsible, read-only first)
- Add an expand/collapse toggle button to each table row (a `›` chevron in a new column before the checkbox, or appended after the last column — decide and document in Architecture Decisions below).
- When expanded, render a nested `<table>` inside a `<tr class="car-stock-subrow">` that shows:
  - Warehouse row: "Warehouse", new count, used count, location string.
  - One row per CarStock record: license plate, condition, quantity.
  - If no CarStock rows: single cell "Not in any car."
- Sub-row is rendered server-side inside the main template (not a separate AJAX fetch for now — keep it simple). It is hidden by default via CSS; JavaScript toggles a class to show/hide.
- **Verify:** part with no car stock shows "Not in any car". Part with car stock (added via admin) shows the correct rows. Toggle works on mobile width.

### Unit 4 — Storage Location filter
- Add a `location` GET parameter to the dashboard view.
- Derive the list of known license plates from `CarStock.objects.values_list('license_plate', flat=True).distinct()` and pass to the template.
- Filter options: `All` (default), `Warehouse Only` (parts where no CarStock rows exist), and one option per distinct license plate (parts where at least one CarStock row has that plate).
- Apply the filter in the dashboard queryset.
- Render the new `<select>` in the filter form between Stock Status and the Search button.
- **Verify:** with two cars in CarStock, filtering by each plate returns only parts in that car. "Warehouse Only" returns only parts with no CarStock rows.

### Unit 5 — Warehouse stock adjustment modal
- Replace the existing direct AJAX call for warehouse +/− with a modal trigger.
- The modal appears before any fetch is made.
- **Adding to warehouse (+1 new or +1 used):**
  - Option A: "Standalone — new part arriving at warehouse"
  - Option B: "Transfer from car — subtract from a car" → shows a `<select>` of license plates currently carrying this part in that condition (fetched from `/get-car-plates/`)
- **Removing from warehouse (−1 new or −1 used):**
  - Option A: "Standalone — part used or discarded"
  - Option B: "Transfer to car — add to a car" → shows a text input for license plate (free text, since it may be a car not yet in CarStock)
- On confirm: fires AJAX to `/part/<id>/adjust/` with extra params (`transfer_plate`, `transfer_direction`) as needed.
- Update `/part/<id>/adjust/` view to handle transfer logic atomically (database transaction).
- Add `/get-car-plates/` AJAX endpoint: returns license plates (and conditions) for a given `part_id` and `condition`.
- Modal is keyboard-dismissible (Escape) and has a Cancel button.
- **Verify:** standalone add/remove still works as before. Transfer add to warehouse subtracts from correct car. Transfer remove from warehouse adds to correct car (creates CarStock row if needed).

### Unit 6 — Car stock adjustment (+/− on sub-row)
- Add staff-only +/− buttons to each car stock row in the sub-row (rendered conditionally on `user.is_staff`).
- Wire buttons to a modal (same modal component as Unit 5, different copy):
  - **Adding to car (+1):**
    - Option A: "Standalone — part going directly into the car"
    - Option B: "Transfer from warehouse — subtract from warehouse stock"
  - **Removing from car (−1):**
    - Option A: "Part used/installed — consumed, no transfer"
    - Option B: "Transfer to warehouse — add to warehouse stock"
- On confirm: fires AJAX to `/part/<id>/adjust-car/` with `license_plate`, `condition`, `delta`, and optional `transfer` flag.
- `/part/<id>/adjust-car/` view: adjust `CarStock.quantity`; if it reaches 0, delete the row; handle warehouse transfer atomically.
- Page reloads after successful adjustment (same pattern as existing warehouse adjust); toast confirms the action.
- **Verify:** adding to car increases sub-row count. Removing to 0 deletes the row and it disappears from the sub-row and the Storage Location filter. Transfer to/from warehouse updates both counts correctly.

### Unit 7 — Car Stock section on Add / Edit Part form
- On the Add Part page, below the existing stock fields, add an optional **Car Stock** section:
  - A repeating fieldset: `License Plate` (text input), `Condition` (select: new/used), `Quantity` (number input, min 1).
  - "+ Add car entry" button appends a new fieldset row via JavaScript.
  - "Remove" button on each row removes it.
  - Hidden inputs submit all entries (consistent with the existing model-number tag pattern).
- Server-side: after saving the Part, iterate the submitted car entries and `get_or_create` + update each `CarStock` row.
- Validate: no duplicate `(license_plate, condition)` pairs within the submitted form.
- On the Edit Part page: pre-render existing `CarStock` rows as editable fieldsets. Removing a row and saving deletes the corresponding `CarStock` record.
- **Verify:** add a part with two car entries → CarStock rows created correctly. Edit a part, remove one car entry → CarStock row deleted. Add a duplicate plate/condition pair → friendly validation error.

### Unit 8 — PDF export with car stock column
- Update the ReportLab PDF builder to include a **Car Stock** column.
- Column content: if no CarStock rows, render "—". Otherwise render each row as `{qty}-{condition}-{plate}`, newline-separated within the cell.
- Adjust column widths to accommodate the new column without breaking the existing 5-rows-per-landscape-A4-page layout. Document the final column-width decisions in Architecture Decisions.
- **Verify:** export a part with no car stock → "—" in car stock column. Export a part with two car entries → both appear. Page count and layout are correct on a multi-page export.

---

## Open Questions

- **Sub-row toggle placement:** Should the expand/collapse chevron be in a dedicated leftmost column (before the checkbox), or appended as an icon inside the last column? Decide before Unit 3.
- **CarStock row deletion at zero:** The spec says delete when quantity hits 0 via adjustment. Confirm this also applies when editing a part and setting a car entry's quantity to 0 in the form — or should the form validation reject quantity 0? Resolve before Unit 7.
- **Transfer modal — new car plate input:** When transferring from warehouse to a car that doesn't yet have a CarStock row, the user types a free-text license plate. Should there be any format validation (e.g. length limit) or is it fully free-text? Resolve before Unit 5.
- **Toast wording for transfers:** Define the exact toast messages for warehouse-to-car and car-to-warehouse transfers (e.g. "1 new unit transferred from Warehouse to LC67824"). Resolve before Unit 5.

---

## Architecture Decisions

- **CarStock as a separate child model (not fields on Part):** A part can be in multiple cars simultaneously with different conditions and quantities. Adding columns to `Part` would not support this multiplicity. `CarStock` with a unique `(part, license_plate, condition)` constraint is the correct normalised structure.
- **Cars are not a first-class model:** License plates are free-text on `CarStock`. The set of known plates is derived from existing rows. This keeps the data model minimal and avoids requiring staff to pre-register cars before using them.
- **Combined totals for badge and banners:** Stock status must reflect all available stock, not just warehouse. A part in a car is still available to the shop. Combined total is the right threshold for "Out of Stock" and "Low In Stock."
- **CarStock row deleted at quantity 0:** Leaving zero-quantity rows would pollute the Storage Location filter and sub-row with ghost entries. Deletion on reaching 0 keeps the data clean.
- **Warehouse ↔ car transfers are atomic (database transaction):** A transfer that adjusts two records must never leave the database in a half-updated state. `transaction.atomic()` wraps both updates in the adjust views.
- **Sub-row rendered server-side (not AJAX-fetched):** For simplicity and to avoid an extra round-trip per row expansion, car stock data is passed to the template with the main queryset (via `prefetch_related('carstock_set')`). JavaScript only toggles visibility.

---

## Session Notes

- The existing `Part.total_new` and `Part.total_used` fields remain as warehouse-only counts. Do not rename them — the existing adjust view, tests, and template references use these names.
- The existing `/part/<id>/adjust/` endpoint must remain backward-compatible (a plain `field` + `delta` POST with no transfer params should still work as a standalone adjustment, so the modal's "Standalone" path requires no breaking changes to the existing endpoint contract).
- The modal component should be implemented as a single shared HTML partial / JS function rather than duplicated for warehouse and car adjust — the copy changes but the structure is the same.
- All new AJAX endpoints must return JSON with at least `{ "value": <new_quantity> }` for consistency with the existing adjust endpoint response shape.
- Public-repo hygiene (2026-10-16): `inventory/settings.py` (SECRET_KEY, ALLOWED_HOSTS domains), `.env`, `db.sqlite3`, `media/`, `asert/` (collected static), `.python-version` are now gitignored AND untracked via `git rm --cached` (files kept on disk; `manage.py check` passes). Changes are staged but not committed — commit + push to take them out of the public repo going forward.
- README rewritten (2026-10-16) as a recruiter-facing portfolio piece: problem statement, feature tour, engineering highlights, structure, routes, setup (notes settings.py is private), deployment, roadmap.