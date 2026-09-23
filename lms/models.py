from django.db import models
from django.conf import settings


# =========================================================
# LMS SUBJECT
# =========================================================

class Subject(models.Model):
    """
    School subject used to organize LMS courses.
    """

    name = models.CharField(
        max_length=100,
        unique=True,
    )

    code = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


# =========================================================
# LMS COURSE
# =========================================================

class Course(models.Model):
    """
    Digital LMS course.

    A course belongs to a subject and can be assigned
    to one or more existing school classes.
    """

    title = models.CharField(
        max_length=200,
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="courses",
    )

    description = models.TextField(
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lms_courses",
    )

    is_published = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


# =========================================================
# COURSE CLASS
# =========================================================

class CourseClass(models.Model):
    """
    Connects an LMS course to an existing school class.

    The school already stores class_name and stream on the
    Student model, so we do not create a duplicate Class model.
    """

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="classes",
    )

    class_name = models.CharField(
        max_length=30,
    )

    stream = models.CharField(
        max_length=20,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "class_name",
            "stream",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "course",
                    "class_name",
                    "stream",
                ],
                name="unique_course_class_stream",
            )
        ]

    def __str__(self):

        if self.stream:
            return (
                f"{self.course.title} - "
                f"{self.class_name} {self.stream}"
            )

        return (
            f"{self.course.title} - "
            f"{self.class_name}"
        )


# =========================================================
# LEARNING RESOURCE
# =========================================================

class LearningResource(models.Model):
    """
    Digital learning resource uploaded by a teacher
    or administrator.
    """

    RESOURCE_TYPE_CHOICES = [
        ("DOCUMENT", "Notes & Documents"),
        ("VIDEO", "Videos"),
        ("LINK", "External Links"),
    ]

    title = models.CharField(
        max_length=200,
    )

    description = models.TextField(
        blank=True,
    )

    resource_type = models.CharField(
        max_length=20,
        choices=RESOURCE_TYPE_CHOICES,
    )

    file = models.FileField(
        upload_to="lms/resources/",
        blank=True,
        null=True,
    )

    external_url = models.URLField(
        blank=True,
        null=True,
    )

    subject = models.CharField(
        max_length=100,
        blank=True,
    )

    class_name = models.CharField(
        max_length=50,
        blank=True,
    )

    is_published = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="lms_resources",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


# =========================================================
# DIGITAL LESSON
# =========================================================

class DigitalLesson(models.Model):
    """
    Digital lesson created by a teacher or administrator.
    """

    title = models.CharField(
        max_length=200,
    )

    subject = models.CharField(
        max_length=100,
        blank=True,
    )

    class_name = models.CharField(
        max_length=50,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    content = models.TextField(
        blank=True,
    )

    video_url = models.URLField(
        blank=True,
        null=True,
    )

    attachment = models.FileField(
        upload_to="lms/lessons/",
        blank=True,
        null=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="digital_lessons",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    is_published = models.BooleanField(
        default=False,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


# =========================================================
# ASSIGNMENT
# =========================================================

class Assignment(models.Model):
    """
    Assignment created by a teacher or administrator.
    """

    title = models.CharField(
        max_length=200,
    )

    subject = models.CharField(
        max_length=100,
        blank=True,
    )

    class_name = models.CharField(
        max_length=50,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    instructions = models.TextField(
        blank=True,
    )

    attachment = models.FileField(
        upload_to="lms/assignments/",
        blank=True,
        null=True,
    )

    due_date = models.DateTimeField(
        blank=True,
        null=True,
    )

    total_marks = models.PositiveIntegerField(
        default=100,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_assignments",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    is_published = models.BooleanField(
        default=False,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


# =========================================================
# ASSIGNMENT SUBMISSION
# =========================================================

class AssignmentSubmission(models.Model):
    """
    Learner submission for an assignment.
    """

    STATUS_CHOICES = [
        ("SUBMITTED", "Submitted"),
        ("MARKED", "Marked"),
        ("RETURNED", "Returned"),
    ]

    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="submissions",
    )

    learner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assignment_submissions",
    )

    answer = models.TextField(
        blank=True,
    )

    attachment = models.FileField(
        upload_to="lms/submissions/",
        blank=True,
        null=True,
    )

    submitted_at = models.DateTimeField(
        auto_now_add=True,
    )

    marks = models.PositiveIntegerField(
        blank=True,
        null=True,
    )

    feedback = models.TextField(
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="SUBMITTED",
    )

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.assignment.title} - {self.learner}"