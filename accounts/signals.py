from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from students.models import Student
from .models import UserProfile


User = get_user_model()


@receiver(post_save, sender=Student)
def create_student_account(sender, instance, created, **kwargs):
    if not created:
        return

    admission_no = (instance.admission_no or "").strip()

    if not admission_no:
        return

    # Don't create a duplicate profile
    if UserProfile.objects.filter(student=instance).exists():
        return

    # Find an existing user with this username
    user = User.objects.filter(username=admission_no).first()

    if user is None:
        user = User.objects.create_user(
            username=admission_no,
            password=admission_no,
        )
    else:
        # If the username already exists, make sure it has a usable password.
        if not user.has_usable_password():
            user.set_password(admission_no)
            user.save()

    UserProfile.objects.create(
        user=user,
        student=instance,
        role="STUDENT",
        custom_role=None,
        is_active=True,
    )