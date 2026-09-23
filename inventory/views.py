from django.contrib.auth.decorators import login_required
from accounts.staff_access import role_permission_required
from django.db.models import Sum, F
from django.shortcuts import render

from .models import (
    InventoryCategory,
    Supplier,
    InventoryItem,
    StockMovement,
    PurchaseRecord,
    Asset,
)


@login_required
@role_permission_required("view_inventoryitem", "inventory")
def inventory_dashboard(request):
    """
    Main Inventory Management Dashboard.
    """

    # =========================================================
    # BASIC COUNTS
    # =========================================================

    total_categories = InventoryCategory.objects.count()
    total_suppliers = Supplier.objects.count()
    total_items = InventoryItem.objects.count()
    total_assets = Asset.objects.count()

    total_stock_movements = StockMovement.objects.count()
    total_purchases = PurchaseRecord.objects.count()


    # =========================================================
    # STOCK INFORMATION
    # =========================================================

    total_stock_quantity = (
        InventoryItem.objects.aggregate(
            total=Sum("quantity")
        )["total"] or 0
    )

    total_stock_value = (
        InventoryItem.objects.aggregate(
            total=Sum(
                F("quantity") * F("unit_cost")
            )
        )["total"] or 0
    )


    # =========================================================
    # LOW STOCK
    # =========================================================

    low_stock_items = InventoryItem.objects.filter(
        quantity__lte=F("minimum_stock"),
        is_active=True,
    ).order_by("quantity")[:8]

    low_stock_count = InventoryItem.objects.filter(
        quantity__lte=F("minimum_stock"),
        is_active=True,
    ).count()


    # =========================================================
    # RECENT ITEMS
    # =========================================================

    items = InventoryItem.objects.select_related(
        "category",
        "supplier",
    ).order_by(
        "-id"
    )[:8]


    # =========================================================
    # RECENT STOCK MOVEMENTS
    # =========================================================

    stock_movements = StockMovement.objects.select_related(
        "item",
    ).order_by(
        "-movement_date"
    )[:8]


    # =========================================================
    # RECENT PURCHASES
    # =========================================================

    purchases = PurchaseRecord.objects.select_related(
        "supplier",
    ).order_by(
        "-purchase_date",
        "-id",
    )[:8]


    # =========================================================
    # RECENT ASSETS
    # =========================================================

    assets = Asset.objects.all().order_by(
        "-id"
    )[:8]


    # =========================================================
    # RECENT SUPPLIERS
    # =========================================================

    suppliers = Supplier.objects.all().order_by(
        "-id"
    )[:6]


    # =========================================================
    # CONTEXT
    # =========================================================

    context = {

        # Counts
        "total_categories": total_categories,
        "total_suppliers": total_suppliers,
        "total_items": total_items,
        "total_assets": total_assets,
        "total_stock_movements": total_stock_movements,
        "total_purchases": total_purchases,

        # Stock
        "total_stock_quantity": total_stock_quantity,
        "total_stock_value": total_stock_value,

        # Low stock
        "low_stock_count": low_stock_count,
        "low_stock_items": low_stock_items,

        # Recent records
        "items": items,
        "stock_movements": stock_movements,
        "purchases": purchases,
        "assets": assets,
        "suppliers": suppliers,
    }


    return render(
        request,
        "inventory/inventory_dashboard.html",
        context,
    )