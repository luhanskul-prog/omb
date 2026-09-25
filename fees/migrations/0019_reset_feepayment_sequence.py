from django.db import migrations

def reset_feepayment_sequence(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            SELECT setval(
                pg_get_serial_sequence('fees_feepayment', 'id'),
                COALESCE((SELECT MAX(id) FROM fees_feepayment), 1),
                true
            )
        """)

class Migration(migrations.Migration):
    dependencies = [
        ("fees", "0018_reset_feerecord_sequence"),
    ]

    operations = [
        migrations.RunPython(
            reset_feepayment_sequence,
            migrations.RunPython.noop,
        ),
    ]
