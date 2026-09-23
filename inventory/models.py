from django.db import models


# =========================================================
# INVENTORY CATEGORY
# =========================================================

class InventoryCategory(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True,
    )

    description = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        verbose_name = "Inventory Category"
        verbose_name_plural = "Inventory Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


# =========================================================
# SUPPLIER
# =========================================================

class Supplier(models.Model):

    name = models.CharField(
        max_length=150,
    )

    contact_person = models.CharField(
        max_length=150,
        blank=True,
    )

    phone = models.CharField(
        max_length=30,
        blank=True,
    )

    email = models.EmailField(
        blank=True,
    )

    address = models.TextField(
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


# =========================================================
# INVENTORY ITEM
# =========================================================

class InventoryItem(models.Model):

    UNIT_CHOICES = [
        ("piece", "Piece"),
        ("box", "Box"),
        ("pack", "Pack"),
        ("ream", "Ream"),
        ("kg", "Kilogram"),
        ("litre", "Litre"),
        ("set", "Set"),
        ("pair", "Pair"),
        ("dozen", "Dozen"),
        ("other", "Other"),
    ]

    category = models.ForeignKey(
        InventoryCategory,
        on_delete=models.PROTECT,
        related_name="items",
    )

    name = models.CharField(
        max_length=200,
    )

    item_code = models.CharField(
        max_length=50,
        unique=True,
    )

    description = models.TextField(
        blank=True,
    )

    unit = models.CharField(
        max_length=20,
        choices=UNIT_CHOICES,
        default="piece",
    )

    quantity = models.PositiveIntegerField(
        default=0,
    )

    minimum_stock = models.PositiveIntegerField(
        default=0,
    )

    unit_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items",
    )

    location = models.CharField(
        max_length=150,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.item_code})"

    @property
    def stock_value(self):
        return self.quantity * self.unit_cost

    @property
    def is_low_stock(self):
        return self.quantity <= self.minimum_stock


# =========================================================
# STOCK MOVEMENT
# =========================================================

class StockMovement(models.Model):

    MOVEMENT_CHOICES = [
        ("received", "Stock Received"),
        ("issued", "Stock Issued"),
        ("adjustment", "Stock Adjustment"),
        ("returned", "Stock Returned"),
    ]

    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.CASCADE,
        related_name="movements",
    )

    movement_type = models.CharField(
        max_length=20,
        choices=MOVEMENT_CHOICES,
    )

    quantity = models.PositiveIntegerField()

    reference_number = models.CharField(
        max_length=100,
        blank=True,
    )

    issued_to = models.CharField(
        max_length=150,
        blank=True,
    )

    department = models.CharField(
        max_length=150,
        blank=True,
    )

    notes = models.TextField(
        blank=True,
    )

    movement_date = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-movement_date"]

    def __str__(self):
        return (
            f"{self.item.name} - "
            f"{self.get_movement_type_display()} - "
            f"{self.quantity}"
        )


# =========================================================
# PURCHASE RECORD
# =========================================================

class PurchaseRecord(models.Model):

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="purchases",
    )

    invoice_number = models.CharField(
        max_length=100,
        blank=True,
    )

    purchase_date = models.DateField()

    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    notes = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-purchase_date"]

    def __str__(self):
        return (
            f"Purchase {self.invoice_number or self.id}"
        )


# =========================================================
# ASSET
# =========================================================

class Asset(models.Model):

    STATUS_CHOICES = [
        ("active", "Active"),
        ("maintenance", "Under Maintenance"),
        ("disposed", "Disposed"),
        ("lost", "Lost"),
    ]

    name = models.CharField(
        max_length=200,
    )

    asset_code = models.CharField(
        max_length=50,
        unique=True,
    )

    category = models.CharField(
        max_length=100,
    )

    description = models.TextField(
        blank=True,
    )

    purchase_date = models.DateField(
        null=True,
        blank=True,
    )

    purchase_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    location = models.CharField(
        max_length=150,
        blank=True,
    )

    assigned_to = models.CharField(
        max_length=150,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active",
    )

    notes = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.asset_code})"