from django.db import migrations


def reset_student_id_sequence(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            SELECT setval(
                pg_get_serial_sequence('students_student', 'id'),
                COALESCE((SELECT MAX(id) FROM students_student), 1),
                true
            )
        """)


class Migration(migrations.Migration):

    dependencies = [
        ("students", "0006_student_is_active"),
    ]

    operations = [
        migrations.RunPython(
            reset_student_id_sequence,
            migrations.RunPython.noop,
        ),
    ]
