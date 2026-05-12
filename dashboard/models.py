from django.db import models
from django.core.exceptions import ValidationError


class ProductType(models.Model):
    """e.g. "Washing Machine", "Refrigerator" """

    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Brand(models.Model):
    """e.g. "Bosch", "LG" — independent of ProductType"""

    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class PartType(models.Model):
    """
    e.g. "Motor" for Washing Machine is distinct from "Motor" for Refrigerator.
    unique_together enforces that.
    """

    name = models.CharField(max_length=150)
    product_type = models.ForeignKey(
        ProductType,
        on_delete=models.CASCADE,  # PartTypes for a deleted ProductType clean up automatically
        related_name="part_types",
    )

    class Meta:
        unique_together = ("name", "product_type")

    def __str__(self):
        return f"{self.name} ({self.product_type})"


class Part(models.Model):
    """Main inventory record — one row per unique part in the warehouse."""

    product_type = models.ForeignKey(
        ProductType,
        on_delete=models.PROTECT,
        related_name="parts",
    )
    brand = models.ForeignKey(
        Brand,
        on_delete=models.PROTECT,
        related_name="parts",
    )
    part_type = models.ForeignKey(
        PartType,
        on_delete=models.PROTECT,
        related_name="parts",
    )
    image = models.ImageField(upload_to="parts/", null=True, blank=True)
    product_model = models.CharField(max_length=100, null=True, blank=True)
    total_new = models.PositiveIntegerField(default=0)
    total_used = models.PositiveIntegerField(default=0)
    size_kg = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    model_number = models.CharField(max_length=100, null=True, blank=True)
    shelf_number = models.PositiveIntegerField()
    column_number = models.CharField(max_length=100, null=True)
    row_number = models.CharField(max_length=100, null=True)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        unique_together = [
            # Two different parts can't share the same product/brand/type combination
            ("product_type", "brand", "part_type"),
            # Two parts can't occupy the exact same shelf location
            ("shelf_number", "column_number", "row_number"),
        ]

    def clean(self):
        # A part must have at least some stock at the time of entry
        if self.total_new == 0 and self.total_used == 0:
            raise ValidationError("A part must have at least one new or used unit.")

        # The chosen PartType must belong to the chosen ProductType.
        # The frontend enforces this via AJAX cascade; this is the safety net.
        if self.part_type_id and self.product_type_id:
            if self.part_type.product_type_id != self.product_type_id:
                raise ValidationError(
                    "The selected Part Type does not belong to the selected Product Type. "
                    f"Expected '{self.product_type}', "
                    f"but '{self.part_type}' belongs to '{self.part_type.product_type}'."
                )

    def __str__(self):
        return f"{self.product_type} — {self.brand} — {self.part_type}"
