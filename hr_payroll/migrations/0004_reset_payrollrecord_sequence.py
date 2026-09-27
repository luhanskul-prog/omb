from django.db import migrations
from django.core.management.color import no_style


def reset_payrollrecord_sequence(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    PayrollRecord = apps.get_model(
        "hr_payroll",
        "PayrollRecord",
    )

    sql_list = schema_editor.connection.ops.sequence_reset_sql(
        no_style(),
        [PayrollRecord],
    )

    with schema_editor.connection.cursor() as cursor:
        for sql in sql_list:
            cursor.execute(sql)


class Migration(migrations.Migration):

    dependencies = [
        ("hr_payroll", "0003_nssfrule_payerelief_payetaxband"),
    ]

    operations = [
        migrations.RunPython(
            reset_payrollrecord_sequence,
            migrations.RunPython.noop,
        ),
    ]
