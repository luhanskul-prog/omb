from django.db import migrations


def repair_inventory_columns(apps, schema_editor):
    models_to_check = [
        apps.get_model("inventory", "Category"),
        apps.get_model("inventory", "Supplier"),
        apps.get_model("inventory", "Item"),
        apps.get_model("inventory", "Asset"),
        apps.get_model("inventory", "Purchase"),
        apps.get_model("inventory", "PurchaseLine"),
        apps.get_model("inventory", "StockMovement"),
    ]

    connection = schema_editor.connection

    for model in models_to_check:
        table_name = model._meta.db_table

        existing_tables = connection.introspection.table_names()

        if table_name not in existing_tables:
            schema_editor.create_model(model)
            continue

        existing_columns = {
            column.name
            for column in connection.introspection.get_table_description(
                connection.cursor(),
                table_name,
            )
        }

        for field in model._meta.local_concrete_fields:
            column_name = field.column

            if column_name not in existing_columns:
                schema_editor.add_field(model, field)


def reverse_repair_inventory_columns(apps, schema_editor):
    # Intentionally empty.
    # This repair must never remove existing production data or columns.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0002_repair_missing_tables"),
    ]

    operations = [
        migrations.RunPython(
            repair_inventory_columns,
            reverse_code=reverse_repair_inventory_columns,
        ),
    ]
