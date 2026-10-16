# Inventory App — Repair-Shop Spare Parts Management

A production Django web app built for a real repair shop to answer one question in seconds: **what is this part, how many do we have (new and used), and exactly where is it — in the warehouse or in which technician's car?**

This is a real internal tool, designed with the shop's staff and shaped by how they actually work: one-tap stock adjustments, warehouse ↔ car transfers, and print-ready PDF exports for stocktaking.

## What it does

- **Instant part lookup** — filter and search by product type, brand, part type, model numbers, stock status, and storage location (warehouse vs. specific car)
- **One-tap stock adjustments** — increment/decrement new & used counts for the warehouse and for individual technician cars, with a confirmation modal distinguishing standalone changes from warehouse ↔ car transfers (applied atomically via `transaction.atomic()`)
- **Car stock tracking** — per-part breakdown of which license plates carry what, with collapsible sub-rows on the dashboard
- **Smart add/edit forms** — create new product types, brands, and part types inline; tag-style model-number input; optional initial car stock
- **PDF export** — selection-based, landscape A4 via ReportLab with embedded part photos, car-stock breakdown, and page numbering
- **Role-based access** — staff get full controls, regular users get read-only + export, superusers get Django admin; login required everywhere, no self-registration
- **Stock health at a glance** — color-coded status badges (In Stock / Low ≤ 2 / Out of Stock) plus persistent shortage banners

## Tech & engineering highlights

| Area | Details |
|---|---|
| Backend | Django 6, Python 3.13, SQLite |
| Frontend | Server-rendered templates, vanilla JS (`fetch`/AJAX), custom CSS, Font Awesome |
| PDF | ReportLab (landscape A4, 5 rows/page, embedded images) |
| Images | `ImageField` + Pillow, served from `/media/` |
| Static | WhiteNoise (`CompressedManifestStaticFilesStorage`) |
| Auth | Django built-in auth, `@login_required`, staff/regular/superuser roles |

Notable design decisions:

- **Normalized data model** — `ProductType` / `Brand` independent, `PartType` scoped per product type, `Part` as the unique triple junction, `PartModelNumber` and `CarStock` as child models. Deletion is `PROTECT`-guarded and admin-only to prevent accidental data loss.
- **Cars are not a first-class model** — license plates live as free text on `CarStock` rows, derived dynamically for filters. No pre-registration friction for staff.
- **Atomic transfers** — every warehouse ↔ car movement updates two records inside a single transaction, so stock can never half-update.
- **Server-rendered sub-rows** — car-stock breakdowns ship with the main queryset (`prefetch_related`), so expanding a row costs zero extra requests.
- **Validation via `full_clean()`** — unique warehouse locations get friendly human-readable errors, not database jargon.

## Project structure

```
├── manage.py
├── inventory/            # Project config (settings kept private — see Setup)
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── dashboard/            # Main app
│   ├── models.py         # ProductType, Brand, PartType, Part, PartModelNumber, CarStock
│   ├── views.py          # Dashboard, add/edit, AJAX adjust, PDF export
│   ├── forms.py
│   ├── admin.py
│   ├── pdf_utils.py      # ReportLab builder
│   └── migrations/
├── templates/
│   ├── partials/         # base, nav
│   ├── dashboard/        # index, add_part, edit_part
│   └── user/             # login, logout
├── static/
│   └── style.css
├── media/                # User uploads (private, gitignored)
└── passenger_wsgi.py     # Shared-hosting entry point
```

## Routes

| URL | Purpose |
|---|---|
| `/` | Parts dashboard with filters, stock banners, export |
| `/add/` | Add a new part |
| `/part/edit/<pk>/` | Edit an existing part |
| `/part/<pk>/adjust/` | AJAX warehouse stock adjustment |
| `/part/<pk>/adjust-car/` | AJAX car stock adjustment |
| `/get-part-types/` | AJAX cascade: part types by product type |
| `/get-car-plates/` | AJAX: license plates carrying a part |
| `/export/` | PDF export (POST) |
| `/login/` · `/logout/` | Auth (login required everywhere) |
| `/admin/` | Django admin (deletion + user management) |

## Setup

> **Note:** `inventory/settings.py`, `.env`, and `db.sqlite3` are intentionally **not in this repo** (they contain secrets and real business data). To run it, create your own settings from a fresh `django-admin startproject` (Django 6) or ask the repo owner for a sanitized copy.

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/, log in, and manage parts. Admin lives at `/admin/`.

## Deployment

Live in production on Namecheap Stellar shared hosting via `passenger_wsgi.py`, with `DEBUG = False`, WhiteNoise for static files, and media served from `/media/`.

## Status & roadmap

The app is in active development. Current work: car-stock tracking (model + admin done; combined totals, sub-rows, transfer modals, form integration, and PDF column rolling out incrementally). Planned ideas include stock movement history, CSV import, and low-stock alerts.
