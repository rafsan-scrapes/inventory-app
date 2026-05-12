from django.contrib import admin
from .models import ProductType, PartType, Brand, Part

# Register your models here.

from django.contrib import admin
from .models import ProductType, Brand, PartType, Part


@admin.register(ProductType)
class ProductTypeAdmin(admin.ModelAdmin):
    search_fields = ["name"]


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    search_fields = ["name"]


@admin.register(PartType)
class PartTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "product_type"]
    list_filter = ["product_type"]
    search_fields = ["name"]


@admin.register(Part)
class PartAdmin(admin.ModelAdmin):
    list_display = [
        "product_type",
        "brand",
        "part_type",
        "total_new",
        "total_used",
        "shelf_number",
        "column_number",
        "row_number",
        "size_kg",
        "model_number",
    ]
    list_filter = ["product_type", "brand"]
    search_fields = ["model_number", "notes"]
