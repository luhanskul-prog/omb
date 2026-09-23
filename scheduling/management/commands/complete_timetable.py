from django.core.management.base import BaseCommand, CommandError

from scheduling.timetable_system import (
    check_timetable,
    generate_smart_draft,
)


class Command(BaseCommand):

    help = (
        "Validate and/or generate the complete "
        "automatic timetable draft."
    )

    def add_arguments(self, parser):

        parser.add_argument(
            "--check",
            action="store_true",
            help="Check timetable feasibility only.",
        )

        parser.add_argument(
            "--generate",
            action="store_true",
            help="Generate a new draft.",
        )

        parser.add_argument(
            "--clear-draft",
            action="store_true",
            help="Archive the current draft first.",
        )

    def handle(self, *args, **options):

        do_check = options.get("check", False)
        do_generate = options.get("generate", False)
        clear_draft = options.get("clear_draft", False)

        if not do_check and not do_generate:
            do_check = True

        if do_check:

            result = check_timetable()

            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "===== TIMETABLE CHECK ====="
                )
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

            if result["valid"]:
                self.stdout.write(
                    self.style.SUCCESS(
                        "TIMETABLE CHECK: READY"
                    )
                )
            else:
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

        if do_generate:

            result = generate_smart_draft(
                clear_existing_draft=clear_draft
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
                self.style.SUCCESS(
                    "Draft created. It has NOT been published."
                )
            )
