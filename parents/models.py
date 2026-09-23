from django.db import models
from django.contrib.auth.models import User
from students.models import Student


class Parent(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="parent"
    )

    full_name = models.CharField(
        max_length=150
    )

    phone = models.CharField(
        max_length=20
    )

    email = models.EmailField(
        blank=True
    )

    children = models.ManyToManyField(
        Student,
        related_name="parents",
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.full_name