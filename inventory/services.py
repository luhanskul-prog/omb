from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import Item, Purchase, StockMovement


@transaction.atomic
def create_stock_movement(*, item_id, movement_type, quantity, unit_cost=Decimal("0"), reference="", reason="", user=None):
    item = Item.objects.select_for_update().get(pk=item_id)
    quantity = Decimal(str(quantity))

    if quantity <= 0:
        raise ValidationError("Quantity must be greater than zero.")

    if movement_type == StockMovement.IN:
        new_balance = item.current_stock + quantity
    elif movement_type == StockMovement.OUT:
        new_balance = item.current_stock - quantity
        if new_balance < 0:
            raise ValidationError(f"Insufficient stock. Available: {item.current_stock} {item.get_unit_display()}.")
    elif movement_type == StockMovement.ADJUSTMENT:
        # For an adjustment, quantity is the new physical count, not a delta.
        new_balance = quantity
    else:
        raise ValidationError("Invalid stock movement type.")

    movement = StockMovement.objects.create(
        item=item,
        movement_type=movement_type,
        quantity=quantity,
        unit_cost=unit_cost or item.purchase_price,
        reference=reference,
        reason=reason,
        balance_after=new_balance,
        moved_at=timezone.now(),
        created_by=user,
    )

    item.current_stock = new_balance
    if movement_type == StockMovement.IN and unit_cost:
        item.purchase_price = unit_cost
    item.save(update_fields=["current_stock", "purchase_price", "updated_at"])
    return movement


@transaction.atomic
def receive_purchase(*, purchase_id, user=None):
    purchase = Purchase.objects.select_for_update().prefetch_related("lines").get(pk=purchase_id)
    if purchase.status != Purchase.DRAFT:
        raise ValidationError("Only draft purchases can be received.")
    if not purchase.lines.exists():
        raise ValidationError("Add at least one purchase line before receiving the purchase.")

    for line in purchase.lines.all():
        create_stock_movement(
            item_id=line.item_id,
            movement_type=StockMovement.IN,
            quantity=line.quantity,
            unit_cost=line.unit_cost,
            reference=purchase.number,
            reason=f"Purchase received from {purchase.supplier.name}",
            user=user,
        )

    purchase.status = Purchase.RECEIVED
    purchase.received_at = timezone.now()
    purchase.received_by = user
    purchase.save(update_fields=["status", "received_at", "received_by", "updated_at"])
    return purchase
