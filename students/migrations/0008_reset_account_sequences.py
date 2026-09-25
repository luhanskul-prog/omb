from django.db import migrations
from django.core.management.color import no_style


def reset_account_sequences(apps, schema_editor):
    UserProfile = apps.get_model("accounts", "UserProfile")
    Student = apps.get_model("students", "Student")

    sql_list = schema_editor.connection.ops.sequence_reset_sql(
        no_style(),
        [UserProfile, Student],
    )

    with schema_editor.connection.cursor() as cursor:
        for sql in sql_list:
            cursor.execute(sql)


class Migration(migrations.Migration):

    dependencies = [
        ("students", "0007_reset_student_id_sequence"),
        ("accounts", "0007_userprofile_timezone"),
    ]

    operations = [
        migrations.RunPython(
            reset_account_sequences,
            migrations.RunPython.noop,
        ),
    ]

