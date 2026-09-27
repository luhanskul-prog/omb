import csv
from decimal import Decimal

from django.contrib import messages
from django.db.models import F, Q, Sum, DecimalField, ExpressionWrapper
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .decorators import inventory_access_required
from .forms import (
    AssetForm, CategoryForm, ItemForm, PurchaseForm, PurchaseLineFormSet,
    StockMovementForm, SupplierForm,
)
from .models import Asset, Category, Item, Purchase, StockMovement, Supplier
from .services import create_stock_movement, receive_purchase


@inventory_access_required
def dashboard(request):
    items = Item.objects.filter(is_active=True).select_related("category")
    total_stock = items.aggregate(total=Sum("current_stock"))["total"] or Decimal("0")
    stock_value = sum((item.stock_value for item in items), Decimal("0"))
    low_stock = items.filter(current_stock__lte=F("reorder_level"))
    context = {
        "item_count": items.count(),
        "total_stock": total_stock,
        "stock_value": stock_value,
        "low_stock_count": low_stock.count(),
        "category_count": Category.objects.filter(is_active=True).count(),
        "supplier_count": Supplier.objects.filter(is_active=True).count(),
        "movement_count": StockMovement.objects.count(),
        "purchase_count": Purchase.objects.count(),
        "asset_count": Asset.objects.count(),
        "recent_items": items.order_by("-created_at")[:6],
        "recent_movements": StockMovement.objects.select_related("item", "created_by")[:8],
        "recent_purchases": Purchase.objects.select_related("supplier")[:6],
        "low_stock": low_stock.order_by("current_stock")[:8],
        "recent_assets": Asset.objects.select_related("category")[:6],
    }
    return render(request, "inventory/dashboard.html", context)


@inventory_access_required
def item_list(request):
    qs = Item.objects.select_related("category")
    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    status = request.GET.get("status", "")
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q) | Q(location__icontains=q))
    if category:
        qs = qs.filter(category_id=category)
    if status == "low":
        qs = qs.filter(current_stock__lte=F("reorder_level"), current_stock__gt=0)
    elif status == "out":
        qs = qs.filter(current_stock=0)
    context = {"items": qs, "categories": Category.objects.filter(is_active=True), "q": q, "selected_category": category, "selected_status": status}
    return render(request, "inventory/item_list.html", context)


@inventory_access_required
def item_create(request):
    form = ItemForm(request.POST or None)
    if form.is_valid():
        item = form.save()
        messages.success(request, f"Item {item.name} created successfully.")
        return redirect("inventory:item_detail", item.pk)
    return render(request, "inventory/form.html", {"form": form, "title": "Add Inventory Item", "back_url": "inventory:item_list"})


@inventory_access_required
def item_edit(request, pk):
    item = get_object_or_404(Item, pk=pk)
    form = ItemForm(request.POST or None, instance=item)
    if form.is_valid():
        form.save()
        messages.success(request, "Inventory item updated successfully.")
        return redirect("inventory:item_detail", item.pk)
    return render(request, "inventory/form.html", {"form": form, "title": f"Edit {item.name}", "back_url": "inventory:item_detail", "back_args": [item.pk]})


@inventory_access_required
def item_detail(request, pk):
    item = get_object_or_404(Item.objects.select_related("category"), pk=pk)
    movements = item.movements.select_related("created_by")[:30]
    return render(request, "inventory/item_detail.html", {"item": item, "movements": movements})


@inventory_access_required
def category_list(request):
    categories = Category.objects.annotate(item_total=Sum("items__current_stock"))
    return render(request, "inventory/category_list.html", {"categories": categories})


@inventory_access_required
def category_create(request):
    form = CategoryForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Category created successfully.")
        return redirect("inventory:category_list")
    return render(request, "inventory/form.html", {"form": form, "title": "Add Category", "back_url": "inventory:category_list"})


@inventory_access_required
def supplier_list(request):
    q = request.GET.get("q", "").strip()
    suppliers = Supplier.objects.all()
    if q:
        suppliers = suppliers.filter(Q(name__icontains=q) | Q(contact_person__icontains=q) | Q(phone__icontains=q))
    return render(request, "inventory/supplier_list.html", {"suppliers": suppliers, "q": q})


@inventory_access_required
def supplier_create(request):
    form = SupplierForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Supplier created successfully.")
        return redirect("inventory:supplier_list")
    return render(request, "inventory/form.html", {"form": form, "title": "Add Supplier", "back_url": "inventory:supplier_list"})


@inventory_access_required
def stock_list(request):
    movements = StockMovement.objects.select_related("item", "created_by")
    q = request.GET.get("q", "").strip()
    movement_type = request.GET.get("type", "")
    if q:
        movements = movements.filter(Q(item__name__icontains=q) | Q(item__sku__icontains=q) | Q(reference__icontains=q))
    if movement_type:
        movements = movements.filter(movement_type=movement_type)
    return render(request, "inventory/stock_list.html", {"movements": movements[:200], "q": q, "movement_type": movement_type, "movement_choices": StockMovement.MOVEMENT_CHOICES})


@inventory_access_required
def stock_create(request):
    form = StockMovementForm(request.POST or None)
    if form.is_valid():
        data = form.cleaned_data
        try:
            create_stock_movement(
                item_id=data["item"].pk,
                movement_type=data["movement_type"],
                quantity=data["quantity"],
                unit_cost=data.get("unit_cost") or data["item"].purchase_price,
                reference=data.get("reference", ""),
                reason=data.get("reason", ""),
                user=request.user,
            )
            messages.success(request, "Stock movement recorded successfully.")
            return redirect("inventory:stock_list")
        except Exception as exc:
            form.add_error(None, str(exc))
    return render(request, "inventory/form.html", {"form": form, "title": "Record Stock Movement", "back_url": "inventory:stock_list"})


@inventory_access_required
def purchase_list(request):
    purchases = Purchase.objects.select_related("supplier")
    return render(request, "inventory/purchase_list.html", {"purchases": purchases})


@inventory_access_required
def purchase_create(request):
    purchase = Purchase()
    if request.method == "POST":
        form = PurchaseForm(request.POST, instance=purchase)
        formset = PurchaseLineFormSet(request.POST, instance=purchase)
        if form.is_valid() and formset.is_valid():
            purchase = form.save()
            formset.instance = purchase
            formset.save()
            messages.success(request, f"Purchase {purchase.number} saved as draft.")
            return redirect("inventory:purchase_detail", purchase.pk)
    else:
        form = PurchaseForm(instance=purchase, initial={"number": f"PO-{timezone.localdate():%Y%m%d}-{Purchase.objects.count()+1:04d}"})
        formset = PurchaseLineFormSet(instance=purchase)
    return render(request, "inventory/purchase_form.html", {"form": form, "formset": formset, "title": "New Purchase"})


@inventory_access_required
def purchase_detail(request, pk):
    purchase = get_object_or_404(Purchase.objects.select_related("supplier", "received_by").prefetch_related("lines__item"), pk=pk)
    return render(request, "inventory/purchase_detail.html", {"purchase": purchase})


@inventory_access_required
def purchase_receive(request, pk):
    purchase = get_object_or_404(Purchase, pk=pk)
    if request.method == "POST":
        try:
            receive_purchase(purchase_id=purchase.pk, user=request.user)
            messages.success(request, f"Purchase {purchase.number} received and stock updated.")
        except Exception as exc:
            messages.error(request, str(exc))
    return redirect("inventory:purchase_detail", pk)


@inventory_access_required
def asset_list(request):
    q = request.GET.get("q", "").strip()
    assets = Asset.objects.select_related("category")
    if q:
        assets = assets.filter(Q(asset_tag__icontains=q) | Q(name__icontains=q) | Q(serial_number__icontains=q) | Q(location__icontains=q))
    return render(request, "inventory/asset_list.html", {"assets": assets, "q": q})


@inventory_access_required
def asset_create(request):
    form = AssetForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Asset registered successfully.")
        return redirect("inventory:asset_list")
    return render(request, "inventory/form.html", {"form": form, "title": "Register Asset", "back_url": "inventory:asset_list"})


@inventory_access_required
def asset_edit(request, pk):
    asset = get_object_or_404(Asset, pk=pk)
    form = AssetForm(request.POST or None, instance=asset)
    if form.is_valid():
        form.save()
        messages.success(request, "Asset updated successfully.")
        return redirect("inventory:asset_list")
    return render(request, "inventory/form.html", {"form": form, "title": f"Edit {asset.name}", "back_url": "inventory:asset_list"})


@inventory_access_required
def inventory_report(request):
    items = Item.objects.select_related("category").filter(is_active=True)
    total_value = sum((i.stock_value for i in items), Decimal("0"))
    context = {
        "items": items,
        "total_value": total_value,
        "low_stock": items.filter(current_stock__lte=F("reorder_level")),
        "total_assets_value": Asset.objects.aggregate(total=Sum("acquisition_cost"))["total"] or Decimal("0"),
    }
    return render(request, "inventory/report.html", context)


@inventory_access_required
def download_items_csv_template(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="inventory_items_template.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "SKU",
        "Item",
        "Category",
        "Unit",
        "Location",
        "Stock",
        "Reorder Level",
        "Purchase Price",
        "Stock Value",
        "Status",
    ])

    return response


@inventory_access_required
def import_items_csv(request):
    if request.method == "GET":
        return render(request, "inventory/import_items.html")

    uploaded_file = request.FILES.get("csv_file")

    if not uploaded_file:
        messages.error(request, "Please select a CSV file.")
        return redirect("inventory:import_items_csv")

    if not uploaded_file.name.lower().endswith(".csv"):
        messages.error(request, "Only CSV files are allowed.")
        return redirect("inventory:import_items_csv")

    try:
        decoded = uploaded_file.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        messages.error(request, "The CSV file must be saved as UTF-8.")
        return redirect("inventory:import_items_csv")

    reader = csv.DictReader(decoded.splitlines())

    required_columns = [
        "SKU",
        "Item",
        "Category",
        "Unit",
        "Location",
        "Stock",
        "Reorder Level",
        "Purchase Price",
        "Stock Value",
        "Status",
    ]

    actual_columns = [column.strip() if column else "" for column in (reader.fieldnames or [])]

    if actual_columns != required_columns:
        messages.error(
            request,
            "CSV columns do not match the Inventory Export format. "
            "Please export the current items CSV and use that format."
        )
        return redirect("inventory:import_items_csv")

    unit_map = {
        "Piece": "piece",
        "Pack": "pack",
        "Box": "box",
        "Ream": "ream",
        "Set": "set",
        "Bottle": "bottle",
        "Kilogram": "kg",
        "Litre": "litre",
        "Other": "other",
    }

    imported = 0
    updated = 0
    errors = []

    for row_number, row in enumerate(reader, start=2):
        try:
            sku = (row.get("SKU") or "").strip()
            name = (row.get("Item") or "").strip()
            category_name = (row.get("Category") or "").strip()
            unit_display = (row.get("Unit") or "").strip()
            location = (row.get("Location") or "").strip()

            if not sku:
                raise ValueError("SKU is required.")
            if not name:
                raise ValueError("Item name is required.")
            if not category_name:
                raise ValueError("Category is required.")
            if unit_display not in unit_map:
                raise ValueError(f"Invalid Unit: {unit_display}")

            stock = Decimal((row.get("Stock") or "0").strip())
            reorder_level = Decimal((row.get("Reorder Level") or "0").strip())
            purchase_price = Decimal((row.get("Purchase Price") or "0").strip())

            if stock < 0:
                raise ValueError("Stock cannot be negative.")
            if reorder_level < 0:
                raise ValueError("Reorder Level cannot be negative.")
            if purchase_price < 0:
                raise ValueError("Purchase Price cannot be negative.")

            category, _ = Category.objects.get_or_create(
                name=category_name,
                defaults={"is_active": True},
            )

            item = Item.objects.filter(sku=sku).first()

            if item:
                item.name = name
                item.category = category
                item.unit = unit_map[unit_display]
                item.location = location
                item.current_stock = stock
                item.reorder_level = reorder_level
                item.purchase_price = purchase_price
                item.save()
                updated += 1
            else:
                Item.objects.create(
                    sku=sku,
                    name=name,
                    category=category,
                    unit=unit_map[unit_display],
                    location=location,
                    current_stock=stock,
                    reorder_level=reorder_level,
                    purchase_price=purchase_price,
                    is_active=True,
                )
                imported += 1

        except Exception as exc:
            errors.append(f"Row {row_number}: {exc}")

    if imported or updated:
        messages.success(
            request,
            f"CSV import completed: {imported} new item(s) added, "
            f"{updated} existing item(s) updated."
        )

    if errors:
        messages.warning(
            request,
            f"{len(errors)} row(s) could not be imported. "
            + " | ".join(errors[:10])
        )

    if not imported and not updated and not errors:
        messages.info(request, "The CSV file contained no item rows.")

    return redirect("inventory:item_list")


@inventory_access_required
def export_items_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="inventory_items.csv"'
    writer = csv.writer(response)
    writer.writerow(["SKU", "Item", "Category", "Unit", "Location", "Stock", "Reorder Level", "Purchase Price", "Stock Value", "Status"])
    for item in Item.objects.select_related("category"):
        writer.writerow([
            item.sku, item.name, item.category.name, item.get_unit_display(), item.location,
            item.current_stock, item.reorder_level, item.purchase_price, item.stock_value,
            item.stock_status,
        ])
    return response
