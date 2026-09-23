from django.core.management.base import BaseCommand

from scheduling.generator import generate_timetable


class Command(BaseCommand):
    help = "Generate an automatic timetable draft."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear-draft",
            action="store_true",
            help="Deactivate existing non-fixed active timetable entries first.",
        )

    def handle(self, *args, **options):

        clear_draft = options.get("clear_draft", False)

        result = generate_timetable(
            clear_existing_draft=clear_draft
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "===== AUTOMATIC TIMETABLE GENERATION ====="
            )
        )

        self.stdout.write(
            f"TOTAL REQUIRED LESSONS = {result['total_required']}"
        )

        self.stdout.write(
            f"LESSONS SCHEDULED = {result['scheduled']}"
        )

        self.stdout.write(
            f"FIXED ENTRIES PRESERVED = {result['fixed_preserved']}"
        )

        self.stdout.write(
            f"UNSCHEDULED ASSIGNMENTS = {len(result['unscheduled'])}"
        )

        if result["unscheduled"]:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "===== UNSCHEDULED LESSONS ====="
                )
            )

            for item in result["unscheduled"]:
                stream = item["stream"] or "-"

                self.stdout.write(
                    f"{item['subject']} | "
                    f"{item['teacher']} | "
                    f"{item['class_name']} {stream} | "
                    f"Required={item['required']} | "
                    f"Scheduled={item['scheduled']} | "
                    f"Remaining={item['remaining']}"
                )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Timetable draft generation completed."
            )
        )