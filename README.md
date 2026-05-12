# Parts Inventory Management

A Django-based web application for managing electronics parts inventory (refrigerators, washing machines, laptops, and their parts like motors, drain hoses, motherboards). Parts are stored in a warehouse organized by shelf/column/row.

## Features

- **Part Management**: Add, edit, and view parts with details like product type, brand, part type, stock quantities, model number, and warehouse location
- **Smart Dropdowns**: Product Type, Brand, and Part Type show a dropdown of existing values plus an option to add new ones dynamically
- **AJAX Cascading**: When selecting Product Type, the Part Type dropdown automatically filters to show only relevant part types
- **Search & Filter**: Filter parts by product type, brand, part type, shelf, column, and row
- **Stock Adjustment**: Increment or decrement new/used stock directly from the inventory list
- **PDF Export**: Export selected parts to a formatted PDF document
- **Image Upload**: Attach images to parts
- **User Authentication**: Login-protected views with Django's authentication system

## Tech Stack

| Layer | Choice |
|-------|--------|
| Backend | Django (Python 3.13), SQLite3 |
| Frontend | HTML, CSS, Vanilla JavaScript |
| PDF Generation | ReportLab |
| Image Processing | Pillow |
| Auth | Django built-in `django.contrib.auth` |
| Deployment | Namecheap Stellar Basic shared hosting |

## Project Structure

```
inventory_management/
├── manage.py              # Django management script
├── db.sqlite3             # SQLite database
├── requirements.txt       # Python dependencies
├── inventory/
│   ├── settings.py        # Django settings
│   ├── urls.py            # Main URL configuration
│   └── wsgi.py            # WSGI application
├── dashboard/             # Main app
│   ├── models.py          # Data models
│   ├── views.py           # View functions
│   ├── urls.py            # App URL routing
│   ├── forms.py           # Django forms
│   ├── admin.py           # Django admin configuration
│   └── pdf_utils.py       # PDF generation utilities
├── templates/
│   ├── partials/          # Reusable templates (base, nav)
│   ├── dashboard/         # Main app templates
│   └── user/              # Login/logout templates
└── static/
    └── style.css          # CSS styles
```

## Data Models

### ProductType
- `name` (unique): e.g., "Washing Machine", "Refrigerator"

### Brand
- `name` (unique): e.g., "Bosch", "LG"

### PartType
- `name`: e.g., "Motor", "Drain Hose"
- `product_type` (FK to ProductType)
- Unique together: (name, product_type)

### Part
- `product_type` (FK, PROTECT)
- `brand` (FK, PROTECT)
- `part_type` (FK, PROTECT)
- `image` (optional)
- `product_model` (optional): e.g., "RS70F65Q1BLV"
- `total_new` (PositiveIntegerField)
- `total_used` (PositiveIntegerField)
- `size_kg` (optional)
- `model_number` (optional)
- `shelf_number` (PositiveIntegerField)
- `column_number` (CharField)
- `row_number` (CharField)
- `notes` (optional)

Unique together:
- (product_type, brand, part_type)
- (shelf_number, column_number, row_number)

## URL Routes

| URL | Name | View |
|-----|------|------|
| `/` | `dashboard-index` | Part list with filters |
| `/add/` | `add-part` | Add new part |
| `/part/edit/<pk>` | `edit-part` | Edit existing part |
| `/part/<pk>/adjust/` | `adjust-stock` | AJAX stock adjustment |
| `/get-part-types/` | `get-part-types` | AJAX: get part types by product |
| `/export/` | `export-pdf` | PDF export (POST) |
| `/login/` | `user-login` | Login page |
| `/logout/` | `user-logout` | Logout (POST) |
| `/admin/` | — | Django admin |

## Setup

1. **Create virtual environment**:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # source .venv/bin/activate  # Linux/Mac
   ```

2. **Install dependencies**:
   ```bash
   pip install django pillow reportlab
   ```

3. **Run migrations**:
   ```bash
   python manage.py migrate
   ```

4. **Create superuser**:
   ```bash
   python manage.py createsuperuser
   ```

5. **Run development server**:
   ```bash
   python manage.py runserver
   ```

6. **Access the application**:
   - Open http://127.0.0.1:8000/ in your browser
   - Log in with your superuser or regular user credentials
   - Access Django admin at http://127.0.0.1:8000/admin/

## User Accounts

- **Superuser**: Full access including `/admin/` for deletion
- **Normal user**: Can add, edit, and export parts (no deletion)

No public user registration — accounts are created manually via `createsuperuser` and Django admin.

## Validation Rules

- `total_new` and `total_used` cannot both be zero
- `part_type.product_type` must match `part.product_type`
- `full_clean()` is called before saving Part instances
- Warehouse location (shelf/column/row) must be unique

## Design Decisions

- **Product Type locked on Edit**: Changing it would orphan the PartType FK, so it's shown as plain text with a hidden input
- **Deletion via `/admin/` only**: Intentional friction to prevent accidental deletions
- **PDF export is selection-based**: Checkboxes per row + "Select All" option, JS injects selected IDs into a hidden form and POSTs to `/export/`
- **Smart dropdowns**: Allow adding new Product Types, Brands, and Part Types directly from the form
- **AJAX cascade**: Part Type dropdown updates when Product Type changes

## Deployment

The app is configured for Namecheap Stellar Basic shared hosting. Key settings:
- Static files served from `/asert/`
- Media files served from `/media/`
- `DEBUG = False` for production (update `ALLOWED_HOSTS` accordingly)