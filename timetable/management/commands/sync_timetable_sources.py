from django.core.management.base import BaseCommand
from timetable.live_sync import sync_timetable_sources


class Command(BaseCommand):
    help = "Synchronize ERP classes, streams, subjects and teachers into Timetabling."

    def handle(self, *args, **options):
        sync_timetable_sources()
        self.stdout.write(
            self.style.SUCCESS(
                "Timetable sources synchronized successfully."
            )
        )
