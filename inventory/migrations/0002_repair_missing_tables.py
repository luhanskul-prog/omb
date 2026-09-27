from django.db import migrations


def repair_inventory_tables(apps, schema_editor):
    Category = apps.get_model("inventory", "Category")
    Supplier = apps.get_model("inventory", "Supplier")
    Item = apps.get_model("inventory", "Item")
    Asset = apps.get_model("inventory", "Asset")
    Purchase = apps.get_model("inventory", "Purchase")
    PurchaseLine = apps.get_model("inventory", "PurchaseLine")
    StockMovement = apps.get_model("inventory", "StockMovement")

    existing_tables = set(schema_editor.connection.introspection.table_names())

    models_in_order = [
        Category,
        Supplier,
        Item,
        Asset,
        Purchase,
        PurchaseLine,
        StockMovement,
    ]

    for model in models_in_order:
        table_name = model._meta.db_table

        if table_name not in existing_tables:
            schema_editor.create_model(model)


def reverse_repair_inventory_tables(apps, schema_editor):
    # Intentionally empty.
    # This repair migration must not delete existing Inventory data.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            repair_inventory_tables,
            reverse_code=reverse_repair_inventory_tables,
        ),
    ]
