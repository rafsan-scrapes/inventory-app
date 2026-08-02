from django import forms
from .models import Part


class PartForm(forms.ModelForm):
    class Meta:
        model = Part
        fields = [
            "image",
            "product_model",
            "total_new",
            "total_used",
            "size_kg",
            "shelf_number",
            "column_number",
            "row_number",
            "notes",
        ]
        widgets = {
            "image": forms.ClearableFileInput(attrs={"accept": "image/*"}),
            "product_model": forms.TextInput(
                attrs={"placeholder": "e.g. RS70F65Q1BLV"}
            ),
            "total_new": forms.NumberInput(attrs={"min": "0", "placeholder": "0"}),
            "total_used": forms.NumberInput(attrs={"min": "0", "placeholder": "0"}),
            "size_kg": forms.TextInput(attrs={"placeholder": "e.g. 5.5kg/9kg"}),
            "shelf_number": forms.TextInput(attrs={"placeholder": "e.g. 2"}),
            "column_number": forms.TextInput(attrs={"placeholder": "e.g. 3, right"}),
            "row_number": forms.TextInput(attrs={"placeholder": "e.g. 1, left"}),
            "notes": forms.Textarea(
                attrs={
                    "rows": "3",
                    "placeholder": "Any additional notes about condition, origin, etc.",
                }
            ),
        }
