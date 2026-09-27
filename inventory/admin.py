from django.contrib import admin

from .models import Asset, Category, Item, Purchase, PurchaseLine, StockMovement, Supplier


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    search_fields = ("name",)
    list_filter = ("is_active",)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "contact_person", "phone", "email", "is_active")
    search_fields = ("name", "contact_person", "phone", "email")
    list_filter = ("is_active",)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("sku", "name", "category", "current_stock", "reorder_level", "purchase_price", "is_active")
    search_fields = ("sku", "name", "location")
    list_filter = ("category", "unit", "is_active")
    readonly_fields = ("current_stock",)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("moved_at", "item", "movement_type", "quantity", "balance_after", "reference", "created_by")
    search_fields = ("item__name", "item__sku", "reference", "reason")
    list_filter = ("movement_type", "moved_at")
    readonly_fields = ("balance_after",)


class PurchaseLineInline(admin.TabularInline):
    model = PurchaseLine
    extra = 0


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ("number", "supplier", "purchase_date", "status", "invoice_number", "received_at")
    search_fields = ("number", "invoice_number", "supplier__name")
    list_filter = ("status", "purchase_date")
    inlines = [PurchaseLineInline]


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("asset_tag", "name", "category", "location", "assigned_to", "status", "acquisition_cost")
    search_fields = ("asset_tag", "name", "serial_number", "location", "assigned_to")
    list_filter = ("status", "category")
