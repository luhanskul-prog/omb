from django.core.management.base import BaseCommand, CommandError
from django.core import serializers
from django.db import transaction
from django.db.models.signals import post_save

from students.models import Student
from accounts.signals import create_student_account


class Command(BaseCommand):
    help = "Load a fixture transactionally while disabling automatic Student account creation."

    def add_arguments(self, parser):
        parser.add_argument("fixture", help="Fixture file/path to load")

    def handle(self, *args, **options):
        fixture = options["fixture"]

        self.stdout.write("Disconnecting Student account signal...")

        post_save.disconnect(
            create_student_account,
            sender=Student,
        )

        try:
            with transaction.atomic():
                self.stdout.write(
                    f"Loading fixture transactionally: {fixture}"
                )

                count = 0

                with open(fixture, "rb") as fixture_file:
                    objects = serializers.deserialize(
                        "json",
                        fixture_file,
                        ignorenonexistent=False,
                    )

                    for obj in objects:
                        obj.save()
                        count += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully loaded {count} objects."
                    )
                )

        except Exception as exc:
            self.stdout.write(
                self.style.ERROR(
                    "IMPORT FAILED — TRANSACTION ROLLED BACK."
                )
            )
            raise CommandError(
                f"Fixture import failed: {exc}"
            ) from exc

        finally:
            post_save.connect(
                create_student_account,
                sender=Student,
            )

            self.stdout.write(
                self.style.SUCCESS(
                    "Student account signal restored."
                )
            )
