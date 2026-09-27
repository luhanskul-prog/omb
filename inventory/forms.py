from django import forms
from django.forms import inlineformset_factory

from .models import Asset, Category, Item, Purchase, PurchaseLine, StockMovement, Supplier


class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"form-control {existing}".strip()
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"


class CategoryForm(StyledModelForm):
    class Meta:
        model = Category
        fields = ["name", "description", "is_active"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class SupplierForm(StyledModelForm):
    class Meta:
        model = Supplier
        fields = ["name", "contact_person", "phone", "email", "address", "kra_pin", "notes", "is_active"]
        widgets = {"address": forms.Textarea(attrs={"rows": 2}), "notes": forms.Textarea(attrs={"rows": 3})}


class ItemForm(StyledModelForm):
    class Meta:
        model = Item
        fields = ["sku", "name", "category", "description", "unit", "current_stock", "location", "reorder_level", "purchase_price", "is_active"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class StockMovementForm(StyledModelForm):
    class Meta:
        model = StockMovement
        fields = ["item", "movement_type", "quantity", "unit_cost", "reference", "reason", "moved_at"]
        widgets = {"moved_at": forms.DateTimeInput(attrs={"type": "datetime-local"})}

    def clean(self):
        cleaned = super().clean()
        movement_type = cleaned.get("movement_type")
        quantity = cleaned.get("quantity")
        item = cleaned.get("item")
        if movement_type == StockMovement.OUT and item and quantity and quantity > item.current_stock:
            raise forms.ValidationError(f"Insufficient stock. Available: {item.current_stock} {item.get_unit_display()}.")
        return cleaned


class PurchaseForm(StyledModelForm):
    class Meta:
        model = Purchase
        fields = ["number", "supplier", "purchase_date", "invoice_number", "notes"]
        widgets = {"purchase_date": forms.DateInput(attrs={"type": "date"}), "notes": forms.Textarea(attrs={"rows": 3})}


class PurchaseLineForm(StyledModelForm):
    class Meta:
        model = PurchaseLine
        fields = ["item", "quantity", "unit_cost"]


PurchaseLineFormSet = inlineformset_factory(
    Purchase,
    PurchaseLine,
    form=PurchaseLineForm,
    extra=1,
    can_delete=True,
)


class AssetForm(StyledModelForm):
    class Meta:
        model = Asset
        fields = ["asset_tag", "name", "category", "serial_number", "location", "assigned_to", "acquisition_date", "acquisition_cost", "status", "notes"]
        widgets = {"acquisition_date": forms.DateInput(attrs={"type": "date"}), "notes": forms.Textarea(attrs={"rows": 3})}
