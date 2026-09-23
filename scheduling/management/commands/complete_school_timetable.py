from django.core.management.base import BaseCommand

from scheduling.complete_timetable_system import (
    check_timetable,
    generate_draft,
)


class Command(BaseCommand):

    help = (
        "Manage the complete school timetable."
    )

    def add_arguments(self, parser):

        parser.add_argument(
            "--check",
            action="store_true",
        )

        parser.add_argument(
            "--generate",
            action="store_true",
        )

        parser.add_argument(
            "--clear-draft",
            action="store_true",
        )

    def handle(
        self,
        *args,
        **options
    ):

        check = options["check"]
        generate = options["generate"]

        if not check and not generate:
            check = True

        if check:

            result = check_timetable()

            self.stdout.write("")
            self.stdout.write(
                "===== COMPLETE TIMETABLE CHECK ====="
            )

            self.stdout.write(
                f"Required lessons: "
                f"{result['required_lessons']}"
            )

            self.stdout.write(
                f"Scheduled lessons: "
                f"{result['scheduled_lessons']}"
            )

            self.stdout.write(
                f"Problems: "
                f"{result['total_problems']}"
            )

            if result["ready"]:

                self.stdout.write(
                    self.style.SUCCESS(
                        "TIMETABLE CHECK: READY"
                    )
                )

            if not result["ready"]:

                self.stdout.write(
                    self.style.ERROR(
                        "TIMETABLE CHECK: PROBLEMS FOUND"
                    )
                )

                for problem in result["problems"]:

                    self.stdout.write(
                        f"[{problem['category']}] "
                        f"{problem['message']}"
                    )

        if generate:

            result = generate_draft(
                clear_existing_draft=
                    options["clear_draft"]
            )

            self.stdout.write("")
            self.stdout.write(
                self.style.SUCCESS(
                    "===== TIMETABLE DRAFT GENERATED ====="
                )
            )

            self.stdout.write(
                f"Version: {result['version'].id}"
            )

            self.stdout.write(
                f"Required: {result['total_required']}"
            )

            self.stdout.write(
                f"Scheduled: {result['scheduled']}"
            )

            self.stdout.write(
                f"Fixed preserved: "
                f"{result['fixed_preserved']}"
            )

            self.stdout.write(
                f"Unscheduled: "
                f"{len(result['unscheduled'])}"
            )

            for item in result["unscheduled"]:

                self.stdout.write(
                    self.style.ERROR(
                        f"UNSCHEDULED: "
                        f"{item['class_name']} "
                        f"{item['stream']} "
                        f"subject={item['subject_id']} "
                        f"teacher={item['teacher_id']} "
                        f"- {item['reason']}"
                    )
                )

            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "Draft created. "
                    "It has NOT been published."
                )
            )
