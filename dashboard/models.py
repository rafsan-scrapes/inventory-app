from django.db import models
from django.core.exceptions import ValidationError


class ProductType(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class PartType(models.Model):
    name = models.CharField(max_length=150)
    product_type = models.ForeignKey(
        ProductType,
        on_delete=models.CASCADE,
        related_name="part_types",
    )

    class Meta:
        unique_together = ("name", "product_type")

    def __str__(self):
        return f"{self.name} ({self.product_type})"


class Part(models.Model):
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
    size_kg = models.CharField(max_length=100, null=True, blank=True)
    shelf_number = models.CharField(max_length=100, null=True)
    column_number = models.CharField(max_length=100, null=True)
    row_number = models.CharField(max_length=100, null=True)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        unique_together = [
            ("product_type", "brand", "part_type"),
            ("shelf_number", "column_number", "row_number"),
        ]

    def clean(self):
        if self.total_new == 0 and self.total_used == 0:
            raise ValidationError("A part must have at least one new or used unit.")

        if self.part_type_id and self.product_type_id:
            if self.part_type.product_type_id != self.product_type_id:
                raise ValidationError(
                    "The selected Part Type does not belong to the selected Product Type. "
                    f"Expected '{self.product_type}', "
                    f"but '{self.part_type}' belongs to '{self.part_type.product_type}'."
                )

    def __str__(self):
        return f"{self.product_type} — {self.brand} — {self.part_type}"

    @property
    def stock_status(self):
        total = self.total_new + self.total_used
        if total == 0:
            return "Out of Stock"
        elif total <= 2:
            return "Low In Stock"
        else:
            return "In Stock"

    @property
    def first_model_number(self):
        first = self.model_numbers.first()
        return first.value if first else None


class PartModelNumber(models.Model):
    part = models.ForeignKey(
        Part,
        on_delete=models.CASCADE,
        related_name="model_numbers",
    )
    value = models.CharField(max_length=100)

    class Meta:
        unique_together = ("part", "value")
        verbose_name = "Part Model Number"
        verbose_name_plural = "Part Model Numbers"

    def __str__(self):
        return self.value


class CarStock(models.Model):
    CONDITION_CHOICES = [
        ("new", "New"),
        ("used", "Used"),
    ]

    part = models.ForeignKey(
        Part,
        on_delete=models.CASCADE,
        related_name="carstock_set",
    )
    license_plate = models.CharField(max_length=50)
    condition = models.CharField(max_length=10, choices=CONDITION_CHOICES)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("part", "license_plate", "condition")
        verbose_name = "Car Stock Entry"
        verbose_name_plural = "Car Stock Entries"

    def __str__(self):
        return f"{self.part} — {self.license_plate} ({self.get_condition_display()})"
