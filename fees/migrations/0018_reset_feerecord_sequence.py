from django.db import migrations
from django.core.management.color import no_style


def reset_feerecord_sequence(apps, schema_editor):
    FeeRecord = apps.get_model("fees", "FeeRecord")

    sql_list = schema_editor.connection.ops.sequence_reset_sql(
        no_style(),
        [FeeRecord],
    )

    with schema_editor.connection.cursor() as cursor:
        for sql in sql_list:
            cursor.execute(sql)


class Migration(migrations.Migration):
    dependencies = [
        ("fees", "0017_mpesapaybilltransaction"),
    ]

    operations = [
        migrations.RunPython(
            reset_feerecord_sequence,
            migrations.RunPython.noop,
        ),
    ]
