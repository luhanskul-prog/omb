from django.db import models


class TimetablePeriod(models.Model):
    name = models.CharField(max_length=100)
    start_time = models.TimeField()
    end_time = models.TimeField()
    order = models.PositiveIntegerField(default=1)
    is_break = models.BooleanField(default=False)
    is_lunch = models.BooleanField(default=False)
    is_activity = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.name} ({self.start_time}-{self.end_time})"


class TimetableDay(models.Model):
    name = models.CharField(max_length=30)
    short_name = models.CharField(max_length=10)
    order = models.PositiveIntegerField(default=1)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.name


class TimetableTerm(models.Model):
    academic_year = models.CharField(max_length=50)
    term_name = models.CharField(max_length=50)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.academic_year} - {self.term_name}"


class TimetableClass(models.Model):
    name = models.CharField(max_length=100)
    stream = models.CharField(max_length=100, blank=True)
    level = models.CharField(max_length=100, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name", "stream"]

    def __str__(self):
        return f"{self.name} {self.stream}".strip()


class TimetableSubject(models.Model):
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=30, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class TimetableTeacher(models.Model):
    employee = models.OneToOneField(
        "hr_payroll.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="timetable_teacher",
    )
    name = models.CharField(max_length=150)
    staff_number = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    active = models.BooleanField(default=True)
    subjects = models.ManyToManyField(
        TimetableSubject,
        blank=True,
        related_name="teachers"
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class TimetableRoom(models.Model):
    ROOM_TYPES = [
        ("CLASSROOM", "Classroom"),
        ("LAB", "Laboratory"),
        ("ICT", "ICT / Computer Room"),
        ("LIBRARY", "Library"),
        ("HALL", "Hall"),
        ("FIELD", "Field"),
        ("OTHER", "Other"),
    ]

    name = models.CharField(max_length=100)
    room_type = models.CharField(
        max_length=30,
        choices=ROOM_TYPES,
        default="CLASSROOM"
    )
    capacity = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class LessonRequirement(models.Model):
    class_group = models.ForeignKey(
        TimetableClass,
        on_delete=models.CASCADE,
        related_name="lesson_requirements"
    )
    subject = models.ForeignKey(
        TimetableSubject,
        on_delete=models.CASCADE,
        related_name="lesson_requirements"
    )
    teacher = models.ForeignKey(
        TimetableTeacher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lesson_requirements"
    )
    room = models.ForeignKey(
        TimetableRoom,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lesson_requirements"
    )
    lessons_per_week = models.PositiveIntegerField(default=1)
    priority = models.PositiveIntegerField(default=50)
    duration_periods = models.PositiveIntegerField(default=1)
    requires_double = models.BooleanField(default=False)
    double_lessons_per_week = models.PositiveIntegerField(
        default=0,
        help_text="Number of double lessons required each week."
    )
    practical = models.BooleanField(default=False)
    preferred_day = models.ForeignKey(
        TimetableDay,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    notes = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return (
            f"{self.class_group} - {self.subject} "
            f"({self.lessons_per_week}/week)"
        )


class TeacherAvailability(models.Model):
    teacher = models.ForeignKey(
        TimetableTeacher,
        on_delete=models.CASCADE,
        related_name="availability"
    )
    day = models.ForeignKey(TimetableDay, on_delete=models.CASCADE)
    period = models.ForeignKey(TimetablePeriod, on_delete=models.CASCADE)
    available = models.BooleanField(default=True)

    class Meta:
        unique_together = ["teacher", "day", "period"]

    def __str__(self):
        return f"{self.teacher} - {self.day} - {self.period}"


class TimetableLesson(models.Model):
    term = models.ForeignKey(
        TimetableTerm,
        on_delete=models.CASCADE,
        related_name="lessons"
    )
    class_group = models.ForeignKey(
        TimetableClass,
        on_delete=models.CASCADE,
        related_name="timetable_lessons"
    )
    subject = models.ForeignKey(
        TimetableSubject,
        on_delete=models.CASCADE
    )
    teacher = models.ForeignKey(
        TimetableTeacher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    room = models.ForeignKey(
        TimetableRoom,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    day = models.ForeignKey(TimetableDay, on_delete=models.CASCADE)
    period = models.ForeignKey(TimetablePeriod, on_delete=models.CASCADE)
    duration_periods = models.PositiveIntegerField(default=1)
    locked = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    version = models.ForeignKey(
        "TimetableVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lessons",
    )
    is_published = models.BooleanField(
        default=False,
        help_text="Whether this lesson is visible to portal users.",
    )
    is_active = models.BooleanField(default=True)
    class Meta:
        ordering = ["day__order", "period__order"]

    def __str__(self):
        return f"{self.class_group} - {self.subject}"


class TimetableConstraint(models.Model):
    CONSTRAINT_TYPES = [
        ("TEACHER", "Teacher"),
        ("CLASS", "Class"),
        ("ROOM", "Room"),
        ("SUBJECT", "Subject"),
        ("DAY", "Day"),
        ("PERIOD", "Period"),
    ]

    name = models.CharField(max_length=150)
    constraint_type = models.CharField(
        max_length=30,
        choices=CONSTRAINT_TYPES
    )
    description = models.TextField(blank=True)
    hard_constraint = models.BooleanField(default=True)
    weight = models.PositiveIntegerField(default=100)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

from . import advanced_models
