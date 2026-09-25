from django.db import migrations
from django.core.management.color import no_style


def reset_parent_sequence(apps, schema_editor):
    Parent = apps.get_model("parents", "Parent")

    sql_list = schema_editor.connection.ops.sequence_reset_sql(
        no_style(),
        [Parent],
    )

    with schema_editor.connection.cursor() as cursor:
        for sql in sql_list:
            cursor.execute(sql)


class Migration(migrations.Migration):

    dependencies = [
        ("students", "0008_reset_account_sequences"),
        ("parents", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            reset_parent_sequence,
            migrations.RunPython.noop,
        ),
    ]
