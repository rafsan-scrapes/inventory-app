from django.contrib import admin
from .models import ProductType, Brand, PartType, Part, PartModelNumber, CarStock


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


class PartModelNumberInline(admin.TabularInline):
    model = PartModelNumber
    extra = 1


class CarStockInline(admin.TabularInline):
    model = CarStock
    extra = 1


@admin.register(Part)
class PartAdmin(admin.ModelAdmin):
    inlines = [PartModelNumberInline, CarStockInline]
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
    ]
    list_filter = ["product_type", "brand"]
    search_fields = ["model_numbers__value", "notes"]
