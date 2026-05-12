from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="dashboard-index"),
    path("part/edit/<int:pk>", views.edit_part, name="edit-part"),
    path("part/<int:pk>/adjust/", views.adjust_stock, name="adjust-stock"),
    path("get-part-types/", views.get_part_types, name="get-part-types"),
    path("export/", views.export_pdf, name="export-pdf"),  # ← new
]
