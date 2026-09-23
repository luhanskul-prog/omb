from django.db import models


class TimetableVersion(models.Model):
    STATUS_DRAFT = "DRAFT"
    STATUS_PUBLISHED = "PUBLISHED"
    STATUS_ARCHIVED = "ARCHIVED"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_PUBLISHED, "Published"),
        (STATUS_ARCHIVED, "Archived"),
    ]

    term = models.ForeignKey(
        "TimetableTerm",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="versions",
    )
    name = models.CharField(max_length=150)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.name} ({self.status})"


class TimetableTeacherClassAssignment(models.Model):
    teacher = models.ForeignKey(
        "TimetableTeacher",
        on_delete=models.CASCADE,
        related_name="class_assignments",
    )
    class_name = models.CharField(max_length=100)
    stream = models.CharField(max_length=100, blank=True, null=True)
    is_class_teacher = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["teacher__name", "class_name", "stream"]
        constraints = [
            models.UniqueConstraint(
                fields=["teacher", "class_name", "stream"],
                name="unique_timetable_teacher_class_assignment",
            )
        ]

    def __str__(self):
        stream = f" - {self.stream}" if self.stream else ""
        role = " | Class Teacher" if self.is_class_teacher else ""
        return f"{self.teacher} - {self.class_name}{stream}{role}"


class TimetableSlotRule(models.Model):
    TYPE_LESSON = "LESSON"
    TYPE_BREAK = "BREAK"
    TYPE_LUNCH = "LUNCH"
    TYPE_GAMES = "GAMES"
    TYPE_ACTIVITY = "ACTIVITY"
    TYPE_ASSEMBLY = "ASSEMBLY"

    TYPE_CHOICES = [
        (TYPE_LESSON, "Lesson"),
        (TYPE_BREAK, "Break"),
        (TYPE_LUNCH, "Lunch"),
        (TYPE_GAMES, "Games"),
        (TYPE_ACTIVITY, "Activity"),
        (TYPE_ASSEMBLY, "Assembly"),
    ]

    day = models.ForeignKey(
        "TimetableDay",
        on_delete=models.CASCADE,
        related_name="slot_rules",
    )
    period = models.ForeignKey(
        "TimetablePeriod",
        on_delete=models.CASCADE,
        related_name="slot_rules",
    )
    slot_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_LESSON,
    )
    is_enabled = models.BooleanField(default=True)
    notes = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["day__order", "period__order"]
        constraints = [
            models.UniqueConstraint(
                fields=["day", "period"],
                name="unique_timetable_app_slot_rule",
            )
        ]

    def __str__(self):
        return f"{self.day} - {self.period} - {self.get_slot_type_display()}"


class TimetableConfiguration(models.Model):
    term = models.OneToOneField(
        "TimetableTerm",
        on_delete=models.PROTECT,
        related_name="configuration",
    )
    name = models.CharField(max_length=150, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name.strip() or str(self.term)


class TimetableConfiguredSlot(models.Model):
    TYPE_LESSON = "LESSON"
    TYPE_BREAK = "BREAK"
    TYPE_LUNCH = "LUNCH"
    TYPE_GAMES = "GAMES"
    TYPE_ACTIVITY = "ACTIVITY"
    TYPE_ASSEMBLY = "ASSEMBLY"

    TYPE_CHOICES = [
        (TYPE_LESSON, "Lesson"),
        (TYPE_BREAK, "Break"),
        (TYPE_LUNCH, "Lunch"),
        (TYPE_GAMES, "Games"),
        (TYPE_ACTIVITY, "Activity"),
        (TYPE_ASSEMBLY, "Assembly"),
    ]

    configuration = models.ForeignKey(
        "TimetableConfiguration",
        on_delete=models.CASCADE,
        related_name="slots",
    )
    period_number = models.PositiveIntegerField(default=1)
    period_name = models.CharField(max_length=50, default="Period 1")
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_LESSON,
    )
    is_enabled = models.BooleanField(default=True)
    notes = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["period_number", "start_time"]
        constraints = [
            models.UniqueConstraint(
                fields=["configuration", "period_number"],
                name="unique_timetable_configured_slot",
            )
        ]

    @property
    def duration_minutes(self):
        from datetime import datetime

        start = datetime.combine(datetime.today(), self.start_time)
        end = datetime.combine(datetime.today(), self.end_time)
        return max(0, int((end - start).total_seconds()) // 60)

    def __str__(self):
        return (
            f"{self.configuration} | {self.period_name} | "
            f"{self.start_time:%H:%M}-{self.end_time:%H:%M} | "
            f"{self.get_slot_type_display()}"
        )


class TimetableAssignmentGroup(models.Model):
    MODE_SEPARATE = "SEPARATE"
    MODE_JOINT = "JOINT"

    MODE_CHOICES = [
        (MODE_SEPARATE, "Separate Class"),
        (MODE_JOINT, "Joint Lesson"),
    ]

    DURATION_SINGLE = "SINGLE"
    DURATION_DOUBLE = "DOUBLE"

    DURATION_CHOICES = [
        (DURATION_SINGLE, "Single Lesson"),
        (DURATION_DOUBLE, "Double Lesson"),
    ]

    configuration = models.ForeignKey(
        "TimetableConfiguration",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="assignment_groups",
    )
    class_name = models.CharField(max_length=100)
    stream = models.CharField(max_length=100, blank=True, null=True)
    lessons_per_week = models.PositiveIntegerField(default=1)
    mode = models.CharField(
        max_length=20,
        choices=MODE_CHOICES,
        default=MODE_SEPARATE,
    )
    duration = models.CharField(
        max_length=20,
        choices=DURATION_CHOICES,
        default=DURATION_SINGLE,
    )
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        stream = f" {self.stream}" if self.stream else ""
        return f"{self.class_name}{stream} - {self.lessons_per_week} lesson(s)"


class TimetableAssignmentMember(models.Model):
    group = models.ForeignKey(
        "TimetableAssignmentGroup",
        on_delete=models.CASCADE,
        related_name="members",
    )
    teacher = models.ForeignKey(
        "TimetableTeacher",
        on_delete=models.CASCADE,
        related_name="assignment_members",
    )
    subject = models.ForeignKey(
        "TimetableSubject",
        on_delete=models.CASCADE,
        related_name="assignment_members",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["subject__name", "teacher__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["group", "teacher", "subject"],
                name="unique_timetable_app_assignment_member",
            )
        ]

    def __str__(self):
        return f"{self.group} - {self.subject} - {self.teacher}"


class TimetableExamSchedule(models.Model):
    EXAM_TYPES = [
        ("CAT", "CAT"),
        ("MIDTERM", "Mid-Term"),
        ("ENDTERM", "End-Term"),
        ("MOCK", "Mock"),
        ("KJSEA", "KJSEA"),
        ("KPSEA", "KPSEA"),
        ("KCSE", "KCSE"),
        ("OTHER", "Other"),
    ]

    exam_name = models.CharField(max_length=150)
    exam_type = models.CharField(
        max_length=30,
        choices=EXAM_TYPES,
        default="OTHER",
    )
    class_group = models.ForeignKey(
        "TimetableClass",
        on_delete=models.CASCADE,
        related_name="exam_schedules",
    )
    subject = models.ForeignKey(
        "TimetableSubject",
        on_delete=models.CASCADE,
        related_name="exam_schedules",
    )
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    room = models.ForeignKey(
        "TimetableRoom",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="exam_schedules",
    )
    invigilator = models.ForeignKey(
        "TimetableTeacher",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="exam_schedules",
    )
    instructions = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "start_time", "class_group__name"]

    def __str__(self):
        return f"{self.exam_name} - {self.class_group} - {self.subject}"


class TimetableTeacherSubstitution(models.Model):
    date = models.DateField()
    day = models.ForeignKey(
        "TimetableDay",
        on_delete=models.CASCADE,
        related_name="substitutions",
    )
    period = models.ForeignKey(
        "TimetablePeriod",
        on_delete=models.CASCADE,
        related_name="substitutions",
    )
    class_group = models.ForeignKey(
        "TimetableClass",
        on_delete=models.CASCADE,
        related_name="substitutions",
    )
    subject = models.ForeignKey(
        "TimetableSubject",
        on_delete=models.CASCADE,
        related_name="substitutions",
    )
    absent_teacher = models.ForeignKey(
        "TimetableTeacher",
        on_delete=models.CASCADE,
        related_name="absent_substitutions",
    )
    substitute_teacher = models.ForeignKey(
        "TimetableTeacher",
        on_delete=models.CASCADE,
        related_name="substitute_assignments",
    )
    reason = models.CharField(max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "period__order"]

    def __str__(self):
        return (
            f"{self.date} - {self.class_group} - "
            f"{self.subject} - {self.substitute_teacher}"
        )
# ==========================================================
# CANONICAL TEACHER SUBJECT / TEACHING ASSIGNMENTS
# ==========================================================

class TimetableTeacherTeachingAssignment(models.Model):
    teacher = models.ForeignKey(
        "timetable.TimetableTeacher",
        on_delete=models.CASCADE,
        related_name="teaching_assignments",
    )

    subject = models.ForeignKey(
        "timetable.TimetableSubject",
        on_delete=models.CASCADE,
        related_name="teacher_assignments",
    )

    class_name = models.CharField(max_length=100)

    stream = models.CharField(
        max_length=100,
        blank=True,
    )

    lessons_per_week = models.PositiveIntegerField(
        default=1,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "class_name",
            "stream",
            "subject__name",
            "teacher__name",
        ]

    def __str__(self):
        stream = f" {self.stream}" if self.stream else ""
        return (
            f"{self.class_name}{stream} | "
            f"{self.subject} | {self.teacher}"
        )


class TimetableTeacherSubject(models.Model):
    teacher = models.ForeignKey(
        "timetable.TimetableTeacher",
        on_delete=models.CASCADE,
        related_name="teacher_subject_links",
    )

    subject = models.ForeignKey(
        "timetable.TimetableSubject",
        on_delete=models.CASCADE,
        related_name="teacher_links",
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["teacher", "subject"],
                name="unique_timetable_teacher_subject",
            )
        ]

    def __str__(self):
        return f"{self.teacher} | {self.subject}"

