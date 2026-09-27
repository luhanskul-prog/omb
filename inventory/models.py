from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Category(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Supplier(TimeStampedModel):
    name = models.CharField(max_length=180)
    contact_person = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    kra_pin = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["name", "phone"], name="unique_supplier_name_phone")
        ]

    def __str__(self):
        return self.name


class Item(TimeStampedModel):
    UNIT_CHOICES = [
        ("piece", "Piece"),
        ("pack", "Pack"),
        ("box", "Box"),
        ("ream", "Ream"),
        ("set", "Set"),
        ("bottle", "Bottle"),
        ("kg", "Kilogram"),
        ("litre", "Litre"),
        ("other", "Other"),
    ]

    sku = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=180)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="items")
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default="piece")
    location = models.CharField(max_length=120, blank=True, help_text="Store room, lab, office, etc.")
    reorder_level = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    purchase_price = models.DecimalField(max_digits=14, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    current_stock = models.DecimalField(max_digits=14, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["sku"]),
            models.Index(fields=["category"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.sku})"

    @property
    def stock_value(self):
        return (self.current_stock or Decimal("0")) * (self.purchase_price or Decimal("0"))

    @property
    def is_low_stock(self):
        return self.current_stock <= self.reorder_level

    @property
    def stock_status(self):
        if self.current_stock <= 0:
            return "out"
        if self.is_low_stock:
            return "low"
        return "ok"


class StockMovement(TimeStampedModel):
    IN = "IN"
    OUT = "OUT"
    ADJUSTMENT = "ADJUSTMENT"
    MOVEMENT_CHOICES = [
        (IN, "Stock In"),
        (OUT, "Stock Out"),
        (ADJUSTMENT, "Adjustment"),
    ]

    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="movements")
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_CHOICES)
    quantity = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    unit_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    reference = models.CharField(max_length=120, blank=True)
    reason = models.CharField(max_length=255, blank=True)
    balance_after = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    moved_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["-moved_at", "-id"]
        indexes = [
            models.Index(fields=["item", "-moved_at"]),
            models.Index(fields=["movement_type", "-moved_at"]),
        ]

    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.item.name} - {self.quantity}"


class Purchase(TimeStampedModel):
    DRAFT = "DRAFT"
    RECEIVED = "RECEIVED"
    CANCELLED = "CANCELLED"
    STATUS_CHOICES = [
        (DRAFT, "Draft"),
        (RECEIVED, "Received"),
        (CANCELLED, "Cancelled"),
    ]

    number = models.CharField(max_length=40, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="purchases")
    purchase_date = models.DateField(default=timezone.localdate)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=DRAFT)
    invoice_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="received_purchases")

    class Meta:
        ordering = ["-purchase_date", "-id"]

    def __str__(self):
        return self.number

    @property
    def total_amount(self):
        return sum((line.total for line in self.lines.all()), Decimal("0"))


class PurchaseLine(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name="lines")
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="purchase_lines")
    quantity = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    unit_cost = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(0)])

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["purchase", "item"], name="unique_purchase_item")
        ]

    @property
    def total(self):
        return self.quantity * self.unit_cost


class Asset(TimeStampedModel):
    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("MAINTENANCE", "Under Maintenance"),
        ("DISPOSED", "Disposed"),
        ("LOST", "Lost"),
    ]

    asset_tag = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=180)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="assets")
    serial_number = models.CharField(max_length=120, blank=True)
    location = models.CharField(max_length=150, blank=True)
    assigned_to = models.CharField(max_length=150, blank=True)
    acquisition_date = models.DateField(null=True, blank=True)
    acquisition_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ACTIVE")
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.asset_tag} - {self.name}"
