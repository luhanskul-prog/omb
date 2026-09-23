from django.db import models
from django.core.exceptions import ValidationError
from students.models import Student


# ============================================================
# SUBJECT
# ============================================================

class Subject(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True
    )

    code = models.CharField(
        max_length=30,
        blank=True,
        null=True
    )

    is_active = models.BooleanField(
        default=True
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


# ============================================================
# TEACHER
# ============================================================

class Teacher(models.Model):

    employee = models.OneToOneField(
        "hr_payroll.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scheduling_teacher",
    )

    name = models.CharField(
        max_length=150
    )

    employee_no = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True
    )

    phone = models.CharField(
        max_length=30,
        blank=True,
        null=True
    )

    email = models.EmailField(
        blank=True,
        null=True
    )

    is_active = models.BooleanField(
        default=True
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


# ============================================================
# ROOM / VENUE
# ============================================================

class Room(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True
    )

    capacity = models.PositiveIntegerField(
        blank=True,
        null=True
    )

    room_type = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    is_active = models.BooleanField(
        default=True
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


# ============================================================
# LESSON PERIOD
# ============================================================

class Period(models.Model):

    name = models.CharField(
        max_length=50
    )

    start_time = models.TimeField()

    end_time = models.TimeField()

    order = models.PositiveIntegerField(
        default=1
    )

    is_break = models.BooleanField(
        default=False
    )

    class Meta:
        ordering = ["order"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "name",
                    "start_time",
                    "end_time"
                ],
                name="unique_period"
            )
        ]

    def __str__(self):

        if self.is_break:
            return f"{self.name} (Break)"

        return (
            f"{self.name} "
            f"({self.start_time.strftime('%H:%M')} - "
            f"{self.end_time.strftime('%H:%M')})"
        )


# ============================================================
# DAYS OF THE WEEK
# ============================================================

class Day(models.Model):

    DAY_CHOICES = [
        ("MONDAY", "Monday"),
        ("TUESDAY", "Tuesday"),
        ("WEDNESDAY", "Wednesday"),
        ("THURSDAY", "Thursday"),
        ("FRIDAY", "Friday"),
        ("SATURDAY", "Saturday"),
        ("SUNDAY", "Sunday"),
    ]

    name = models.CharField(
        max_length=20,
        choices=DAY_CHOICES,
        unique=True
    )

    order = models.PositiveIntegerField(
        default=1
    )

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.get_name_display()


# ============================================================
# TEACHER CLASS ASSIGNMENT
# ============================================================

class TeacherClassAssignment(models.Model):

    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name="class_assignments",
    )

    class_name = models.CharField(
        max_length=100
    )

    stream = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    is_class_teacher = models.BooleanField(
        default=False
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = [
            "teacher__name",
            "class_name",
            "stream",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "teacher",
                    "class_name",
                    "stream",
                ],
                name="unique_teacher_class_assignment",
            )
        ]

    def __str__(self):

        stream_text = (
            f" - {self.stream}"
            if self.stream
            else ""
        )

        class_teacher_text = (
            " | Class Teacher"
            if self.is_class_teacher
            else ""
        )

        return (
            f"{self.teacher} - "
            f"{self.class_name}"
            f"{stream_text}"
            f"{class_teacher_text}"
        )


# ============================================================
# TEACHER TEACHING ASSIGNMENT
# ============================================================

class TeacherTeachingAssignment(models.Model):

    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name="teaching_assignments",
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="teaching_class_assignments",
    )

    class_name = models.CharField(
        max_length=100
    )

    stream = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    lessons_per_week = models.PositiveIntegerField(
        default=1,
        help_text="Number of lessons this teacher should teach this subject to this class each week."
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = [
            "teacher__name",
            "class_name",
            "stream",
            "subject__name",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "teacher",
                    "subject",
                    "class_name",
                    "stream",
                ],
                name="unique_teacher_teaching_assignment",
            )
        ]

    def __str__(self):

        stream_text = (
            f" - {self.stream}"
            if self.stream
            else ""
        )

        return (
            f"{self.teacher} - "
            f"{self.subject} - "
            f"{self.class_name}"
            f"{stream_text}"
        )

# ============================================================
# TIMETABLE ENTRY
# ============================================================


class TeacherSubject(models.Model):
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name="subject_assignments",
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="teacher_assignments",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = [
            "teacher__name",
            "subject__name",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["teacher", "subject"],
                name="unique_teacher_subject_assignment",
            )
        ]

    def __str__(self):
        return f"{self.teacher} - {self.subject}"


class TimetableVersion(models.Model):
    STATUS_DRAFT = "DRAFT"
    STATUS_PUBLISHED = "PUBLISHED"
    STATUS_ARCHIVED = "ARCHIVED"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_PUBLISHED, "Published"),
        (STATUS_ARCHIVED, "Archived"),
    ]

    name = models.CharField(
        max_length=150,
        help_text="Human-readable name for this timetable version."
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(blank=True, null=True)
    archived_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.name} ({self.status})"

# ============================================================
# COMPLETE TIMETABLE MANAGEMENT MODELS
# ============================================================

class TimetableAssignmentGroup(models.Model):

    configuration = models.ForeignKey(
        "TimetableConfiguration",
        on_delete=models.CASCADE,
        related_name="assignment_groups",
        null=True,
        blank=True,
    )

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

    class_name = models.CharField(
        max_length=100
    )

    stream = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    lessons_per_week = models.PositiveIntegerField(
        default=1
    )

    mode = models.CharField(
        max_length=20,
        choices=MODE_CHOICES,
        default=MODE_SEPARATE
    )

    duration = models.CharField(
        max_length=20,
        choices=DURATION_CHOICES,
        default=DURATION_SINGLE
    )

    is_active = models.BooleanField(
        default=True
    )

    notes = models.TextField(
        blank=True,
        default=""
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = [
            "class_name",
            "stream",
            "-created_at",
        ]

    def __str__(self):
        target = self.class_name

        if self.stream:
            target = f"{target} {self.stream}"

        return (
            f"{target} - "
            f"{self.lessons_per_week} lesson(s) - "
            f"{self.get_mode_display()}"
        )


class TimetableAssignmentMember(models.Model):

    group = models.ForeignKey(
        TimetableAssignmentGroup,
        on_delete=models.CASCADE,
        related_name="members"
    )

    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name="timetable_assignment_members"
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="timetable_assignment_members"
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = [
            "subject__name",
            "teacher__name",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "group",
                    "teacher",
                    "subject",
                ],
                name="unique_timetable_assignment_member"
            )
        ]

    def __str__(self):
        return (
            f"{self.group} - "
            f"{self.subject} - "
            f"{self.teacher}"
        )



# ============================================================
# TIMETABLE MANAGEMENT CONFIGURATION
# ============================================================

class TimetableConfiguration(models.Model):

    academic_year = models.ForeignKey(
        "fees.AcademicYear",
        on_delete=models.PROTECT,
        related_name="timetable_configurations",
    )

    term = models.ForeignKey(
        "fees.Term",
        on_delete=models.PROTECT,
        related_name="timetable_configurations",
    )

    name = models.CharField(
        max_length=150,
        blank=True,
        default="",
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = [
            "-academic_year__year",
            "term__order",
            "-id",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "academic_year",
                    "term",
                ],
                name="unique_timetable_configuration_year_term",
            )
        ]

    def __str__(self):
        label = self.name.strip()

        if label:
            return label

        return (
            f"{self.academic_year.year} - "
            f"{self.term.name}"
        )


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
        TimetableConfiguration,
        on_delete=models.CASCADE,
        related_name="slots",
    )

    period_number = models.PositiveIntegerField(
        default=1
    )

    period_name = models.CharField(
        max_length=50,
        default="Period 1",
    )

    start_time = models.TimeField()

    end_time = models.TimeField()

    slot_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_LESSON,
    )

    is_enabled = models.BooleanField(
        default=True
    )

    notes = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = [
            "period_number",
            "start_time",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "configuration",
                    "period_number",
                ],
                name="unique_configured_timetable_slot",
            )
        ]

    @property
    def duration_minutes(self):
        from datetime import datetime

        start = datetime.combine(
            datetime.today(),
            self.start_time,
        )

        end = datetime.combine(
            datetime.today(),
            self.end_time,
        )

        seconds = int(
            (end - start).total_seconds()
        )

        return max(
            0,
            seconds // 60
        )

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.end_time <= self.start_time:
            raise ValidationError(
                {
                    "end_time": (
                        "End time must be later than "
                        "start time."
                    )
                }
            )

        if self.period_number < 1:
            raise ValidationError(
                {
                    "period_number": (
                        "Period number must be greater than zero."
                    )
                }
            )

    def __str__(self):
        return (
            f"{self.configuration} | "
            f"{self.day} | "
            f"{self.period_name} | "
            f"{self.start_time.strftime('%I:%M %p')} - "
            f"{self.end_time.strftime('%I:%M %p')} | "
            f"{self.get_slot_type_display()}"
        )


class TimetableSlotRule(models.Model):

    TYPE_LESSON = "LESSON"
    TYPE_BREAK = "BREAK"
    TYPE_LUNCH = "LUNCH"
    TYPE_GAMES = "GAMES"
    TYPE_ACTIVITY = "ACTIVITY"

    TYPE_CHOICES = [
        (TYPE_LESSON, "Lesson"),
        (TYPE_BREAK, "Break"),
        (TYPE_LUNCH, "Lunch"),
        (TYPE_GAMES, "Games"),
        (TYPE_ACTIVITY, "Activity"),
    ]

    day = models.ForeignKey(
        Day,
        on_delete=models.CASCADE,
        related_name="timetable_slot_rules"
    )

    period = models.ForeignKey(
        Period,
        on_delete=models.CASCADE,
        related_name="timetable_slot_rules"
    )

    slot_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_LESSON
    )

    is_enabled = models.BooleanField(
        default=True
    )

    notes = models.CharField(
        max_length=255,
        blank=True,
        default=""
    )

    class Meta:
        ordering = [
            "day__order",
            "period__order",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "day",
                    "period",
                ],
                name="unique_timetable_slot_rule"
            )
        ]

    def __str__(self):
        return (
            f"{self.day} - "
            f"{self.period} - "
            f"{self.get_slot_type_display()}"
        )

class TimetableEntry(models.Model):

    class_name = models.CharField(
        max_length=100
    )

    stream = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="timetable_entries"
    )

    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="timetable_entries"
    )

    day = models.ForeignKey(
        Day,
        on_delete=models.CASCADE,
        related_name="timetable_entries"
    )

    period = models.ForeignKey(
        Period,
        on_delete=models.CASCADE,
        related_name="timetable_entries"
    )

    room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="timetable_entries"
    )

    notes = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    # --------------------------------------------------------
    # ASC STYLE OPTIONS
    # --------------------------------------------------------

    is_double_period = models.BooleanField(
        default=False
    )

    is_fixed = models.BooleanField(
        default=False
    )

    version = models.ForeignKey(
        "TimetableVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="entries",
    )

    is_published = models.BooleanField(
        default=False,
        help_text="Whether this timetable entry is visible to portal users."
    )
    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = [
            "day__order",
            "period__order",
            "class_name",
        ]

    def __str__(self):

        stream_text = (
            f" - {self.stream}"
            if self.stream
            else ""
        )

        return (
            f"{self.class_name}"
            f"{stream_text} - "
            f"{self.subject} - "
            f"{self.day} - "
            f"{self.period}"
        )

    # --------------------------------------------------------
    # DISPLAY CLASS
    # --------------------------------------------------------

    @property
    def full_class_name(self):

        if self.stream:
            return f"{self.class_name} {self.stream}"

        return self.class_name

    # --------------------------------------------------------
    # CLASH DETECTION
    # --------------------------------------------------------

    def clean(self):
        if not self.day_id or not self.period_id:
            return

        from django.db.models import Q

        conflicts = TimetableEntry.objects.filter(
            day=self.day,
            period=self.period,
            is_active=True,
        ).exclude(
            pk=self.pk
        )

        # Fixed entries are global blockers.
        if self.is_fixed:
            conflicts = conflicts.filter(
                Q(is_fixed=True) |
                Q(version__isnull=True) |
                Q(version__isnull=False)
            )

        # Versionless entries are also global blockers.
        elif self.version_id is None:
            conflicts = conflicts.filter(
                Q(is_fixed=True) |
                Q(version__isnull=True) |
                Q(version__isnull=False)
            )

        # Versioned entries conflict with:
        #   1. fixed entries,
        #   2. versionless/global entries,
        #   3. entries in the same version.
        else:
            conflicts = conflicts.filter(
                Q(is_fixed=True) |
                Q(version__isnull=True) |
                Q(version_id=self.version_id)
            )

        #
        # CLASS CLASH
        #
        class_clash = conflicts.filter(
            class_name=self.class_name,
            stream=self.stream,
        ).exists()

        if class_clash:
            raise ValidationError(
                "This class already has a lesson "
                "scheduled for this day and period."
            )

        #
        # TEACHER CLASH
        #
        if self.teacher_id:
            teacher_clash = conflicts.filter(
                teacher=self.teacher,
            ).exists()

            if teacher_clash:
                raise ValidationError(
                    "This teacher is already assigned "
                    "to another class during this period."
                )

        #
        # ROOM CLASH
        #
        if self.room_id:
            room_clash = conflicts.filter(
                room=self.room,
            ).exists()

            if room_clash:
                raise ValidationError(
                    "This room is already occupied "
                    "during this period."
                )

    def save(self, *args, **kwargs):

        self.full_clean()

        super().save(
            *args,
            **kwargs
        )


# ============================================================
# EXAM SCHEDULE
# ============================================================

class ExamSchedule(models.Model):

    EXAM_TYPE_CHOICES = [
        ("CAT", "CAT"),
        ("MIDTERM", "Mid-Term"),
        ("ENDTERM", "End-Term"),
        ("MOCK", "Mock"),
        ("KJSEA", "KJSEA"),
        ("KPSEA", "KPSEA"),
        ("KCSE", "KCSE"),
        ("OTHER", "Other"),
    ]

    exam_name = models.CharField(
        max_length=150
    )

    exam_type = models.CharField(
        max_length=30,
        choices=EXAM_TYPE_CHOICES,
        default="OTHER"
    )

    class_name = models.CharField(
        max_length=100
    )

    stream = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="exam_schedules"
    )

    date = models.DateField()

    start_time = models.TimeField()

    end_time = models.TimeField()

    room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="exam_schedules"
    )

    invigilator = models.ForeignKey(
        Teacher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invigilated_exams"
    )

    instructions = models.TextField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = [
            "date",
            "start_time",
            "class_name",
        ]

    def __str__(self):

        return (
            f"{self.exam_name} - "
            f"{self.class_name} - "
            f"{self.subject}"
        )


# ============================================================
# TEACHER SUBSTITUTION
# ============================================================

class TeacherSubstitution(models.Model):

    date = models.DateField()

    day = models.ForeignKey(
        Day,
        on_delete=models.CASCADE,
        related_name="substitutions"
    )

    period = models.ForeignKey(
        Period,
        on_delete=models.CASCADE,
        related_name="substitutions"
    )

    class_name = models.CharField(
        max_length=100
    )

    stream = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="substitutions"
    )

    absent_teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name="absent_substitutions"
    )

    substitute_teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name="substitute_assignments"
    )

    reason = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    notes = models.TextField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = [
            "-date",
            "period__order",
        ]

    def __str__(self):

        return (
            f"{self.date} - "
            f"{self.class_name} - "
            f"{self.subject} - "
            f"{self.substitute_teacher}"
        )



