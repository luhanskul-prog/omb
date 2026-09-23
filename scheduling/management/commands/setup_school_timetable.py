from django.core.management.base import BaseCommand
from scheduling.models import Day, Period


class Command(BaseCommand):
    help = "Create the standard school timetable days and periods."

    def handle(self, *args, **options):

        days = [
            ("MONDAY", 1),
            ("TUESDAY", 2),
            ("WEDNESDAY", 3),
            ("THURSDAY", 4),
            ("FRIDAY", 5),
        ]

        for name, order in days:
            Day.objects.update_or_create(
                name=name,
                defaults={"order": order},
            )

        periods = [
            ("Period 1", "08:00", "08:40", 1, False),
            ("Period 2", "08:40", "09:20", 2, False),
            ("Period 3", "09:20", "10:00", 3, False),
            ("Morning Break", "10:00", "10:20", 4, True),
            ("Period 4", "10:20", "11:00", 5, False),
            ("Period 5", "11:00", "11:40", 6, False),
            ("Period 6", "11:40", "12:20", 7, False),
            ("Lunch Break", "12:20", "13:20", 8, True),
            ("Period 7", "13:20", "14:00", 9, False),
            ("Period 8", "14:00", "14:40", 10, False),
        ]

        for name, start, end, order, is_break in periods:
            Period.objects.update_or_create(
                name=name,
                defaults={
                    "start_time": start,
                    "end_time": end,
                    "order": order,
                    "is_break": is_break,
                },
            )

        self.stdout.write(self.style.SUCCESS(
            "School timetable structure created successfully."
        ))

        self.stdout.write(
            f"Days configured: {Day.objects.count()}"
        )

        self.stdout.write(
            f"Periods configured: {Period.objects.count()}"
        )

        self.stdout.write(
            f"Teaching periods: {Period.objects.filter(is_break=False).count()}"
        )

        self.stdout.write(
            f"Break periods: {Period.objects.filter(is_break=True).count()}"
        )