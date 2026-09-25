from django.db import migrations
from django.core.management.color import no_style


def reset_attendance_sequence(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    Attendance = apps.get_model("attendance", "Attendance")

    sql_list = schema_editor.connection.ops.sequence_reset_sql(
        no_style(),
        [Attendance],
    )

    with schema_editor.connection.cursor() as cursor:
        for sql in sql_list:
            cursor.execute(sql)


class Migration(migrations.Migration):
    dependencies = [
        ("attendance", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            reset_attendance_sequence,
            migrations.RunPython.noop,
        ),
    ]
