from django.db import migrations, models
import django.db.models.deletion


def create_initial_year_and_terms(apps, schema_editor):
    AcademicYear = apps.get_model("fees", "AcademicYear")
    Term = apps.get_model("fees", "Term")
    FeeRecord = apps.get_model("fees", "FeeRecord")

    # Create Academic Year 2026
    academic_year, created = AcademicYear.objects.get_or_create(
        year=2026,
        defaults={"is_active": True},
    )

    # Create the three standard terms
    term1, created = Term.objects.get_or_create(
        name="Term 1",
        defaults={
            "order": 1,
            "is_active": True,
        },
    )

    term2, created = Term.objects.get_or_create(
        name="Term 2",
        defaults={
            "order": 2,
            "is_active": True,
        },
    )

    term3, created = Term.objects.get_or_create(
        name="Term 3",
        defaults={
            "order": 3,
            "is_active": True,
        },
    )

    # Convert existing fee records
    for record in FeeRecord.objects.all():

        old_year = getattr(
            record,
            "old_academic_year",
            "2026"
        )

        old_term = getattr(
            record,
            "old_term",
            "1"
        )

        try:
            year_number = int(old_year)
        except (ValueError, TypeError):
            year_number = 2026

        academic_year_obj, created = AcademicYear.objects.get_or_create(
            year=year_number,
            defaults={"is_active": True},
        )

        if str(old_term).strip() in ["1", "Term 1"]:
            term_obj = term1
        elif str(old_term).strip() in ["2", "Term 2"]:
            term_obj = term2
        elif str(old_term).strip() in ["3", "Term 3"]:
            term_obj = term3
        else:
            term_obj = term1

        record.academic_year = academic_year_obj
        record.term = term_obj
        record.save(
            update_fields=["academic_year", "term"]
        )


class Migration(migrations.Migration):

    dependencies = [
        ("fees", "0001_initial"),
    ]

    operations = [

        # Create AcademicYear table
        migrations.CreateModel(
            name="AcademicYear",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "year",
                    models.PositiveIntegerField(
                        unique=True
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True
                    ),
                ),
            ],
            options={
                "ordering": ["-year"],
            },
        ),

        # Create Term table
        migrations.CreateModel(
            name="Term",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        max_length=50
                    ),
                ),
                (
                    "order",
                    models.PositiveIntegerField(
                        default=1
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True
                    ),
                ),
            ],
            options={
                "ordering": ["order"],
            },
        ),

        # Preserve the old values
        migrations.RenameField(
            model_name="feerecord",
            old_name="academic_year",
            new_name="old_academic_year",
        ),

        migrations.RenameField(
            model_name="feerecord",
            old_name="term",
            new_name="old_term",
        ),

        # Add the new Academic Year relationship
        migrations.AddField(
            model_name="feerecord",
            name="academic_year",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="fee_records",
                to="fees.academicyear",
            ),
        ),

        # Add the new Term relationship
        migrations.AddField(
            model_name="feerecord",
            name="term",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="fee_records",
                to="fees.term",
            ),
        ),

        # Create years/terms and migrate existing records
        migrations.RunPython(
            create_initial_year_and_terms,
            migrations.RunPython.noop,
        ),

        # Remove old amount_paid field.
        # Payments are now calculated from FeePayment.
        migrations.RemoveField(
            model_name="feerecord",
            name="amount_paid",
        ),
    ]