from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User

from students.models import Student
from accounts.models import UserProfile


class Command(BaseCommand):

    help = "Create a login account for a student"

    def add_arguments(self, parser):
        parser.add_argument(
            "admission_no",
            type=str
        )

        parser.add_argument(
            "--password",
            type=str,
            required=True
        )

    def handle(self, *args, **options):

        admission_no = options["admission_no"]
        password = options["password"]

        try:
            student = Student.objects.get(
                admission_no=admission_no
            )
        except Student.DoesNotExist:
            raise CommandError(
                f"Student {admission_no} does not exist."
            )

        username = student.admission_no.lower()

        if User.objects.filter(username=username).exists():
            raise CommandError(
                f"Username {username} already exists."
            )

        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=student.first_name,
            last_name=student.last_name
        )

        UserProfile.objects.create(
            user=user,
            role="STUDENT",
            student=student
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Student account created successfully."
            )
        )

        self.stdout.write(
            f"Username: {username}"
        )