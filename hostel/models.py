from django.db import models


# =========================================================
# HOSTEL
# =========================================================

class Hostel(models.Model):

    HOSTEL_TYPE_CHOICES = [
        ("boys", "Boys"),
        ("girls", "Girls"),
        ("mixed", "Mixed"),
    ]

    name = models.CharField(
        max_length=100,
        unique=True,
    )

    hostel_type = models.CharField(
        max_length=20,
        choices=HOSTEL_TYPE_CHOICES,
        default="mixed",
    )

    location = models.CharField(
        max_length=150,
        blank=True,
    )

    capacity = models.PositiveIntegerField(
        default=0,
    )

    warden_name = models.CharField(
        max_length=150,
        blank=True,
    )

    warden_phone = models.CharField(
        max_length=30,
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
        verbose_name = "Hostel"
        verbose_name_plural = "Hostels"

    def __str__(self):
        return self.name


# =========================================================
# ROOM
# =========================================================

class Room(models.Model):

    ROOM_TYPE_CHOICES = [
        ("standard", "Standard"),
        ("special", "Special"),
        ("staff", "Staff"),
    ]

    hostel = models.ForeignKey(
        Hostel,
        on_delete=models.CASCADE,
        related_name="rooms",
    )

    room_number = models.CharField(
        max_length=30,
    )

    room_type = models.CharField(
        max_length=20,
        choices=ROOM_TYPE_CHOICES,
        default="standard",
    )

    capacity = models.PositiveIntegerField(
        default=1,
    )

    floor = models.CharField(
        max_length=30,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    notes = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["hostel", "room_number"]
        unique_together = ("hostel", "room_number")
        verbose_name = "Hostel Room"
        verbose_name_plural = "Hostel Rooms"

    def __str__(self):
        return f"{self.hostel.name} - Room {self.room_number}"


# =========================================================
# BED
# =========================================================

class Bed(models.Model):

    STATUS_CHOICES = [
        ("available", "Available"),
        ("occupied", "Occupied"),
        ("reserved", "Reserved"),
        ("maintenance", "Maintenance"),
    ]

    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name="beds",
    )

    bed_number = models.CharField(
        max_length=30,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="available",
    )

    notes = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["room", "bed_number"]
        unique_together = ("room", "bed_number")
        verbose_name = "Bed"
        verbose_name_plural = "Beds"

    def __str__(self):
        return f"{self.room} - Bed {self.bed_number}"


# =========================================================
# STUDENT HOSTEL ALLOCATION
# =========================================================

class StudentHostelAllocation(models.Model):

    STATUS_CHOICES = [
        ("active", "Active"),
        ("ended", "Ended"),
        ("transferred", "Transferred"),
    ]

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="hostel_allocations",
    )

    hostel = models.ForeignKey(
        Hostel,
        on_delete=models.CASCADE,
        related_name="student_allocations",
    )

    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name="student_allocations",
    )

    bed = models.ForeignKey(
        Bed,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_allocations",
    )

    admission_date = models.DateField()

    leaving_date = models.DateField(
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active",
    )

    remarks = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-admission_date"]
        verbose_name = "Student Hostel Allocation"
        verbose_name_plural = "Student Hostel Allocations"

    def __str__(self):
        return f"{self.student} - {self.hostel.name} - Room {self.room.room_number}"


# =========================================================
# HOSTEL ATTENDANCE
# =========================================================

class HostelAttendance(models.Model):

    STATUS_CHOICES = [
        ("present", "Present"),
        ("absent", "Absent"),
        ("late", "Late"),
        ("permission", "Out With Permission"),
    ]

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="hostel_attendance",
    )

    hostel = models.ForeignKey(
        Hostel,
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )

    date = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="present",
    )

    remarks = models.TextField(
        blank=True,
    )

    recorded_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-date"]
        unique_together = ("student", "date")
        verbose_name = "Hostel Attendance"
        verbose_name_plural = "Hostel Attendance Records"

    def __str__(self):
        return f"{self.student} - {self.date} - {self.status}"


# =========================================================
# HOSTEL INCIDENT
# =========================================================

class HostelIncident(models.Model):

    SEVERITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="hostel_incidents",
        null=True,
        blank=True,
    )

    hostel = models.ForeignKey(
        Hostel,
        on_delete=models.CASCADE,
        related_name="incidents",
    )

    title = models.CharField(
        max_length=150,
    )

    description = models.TextField()

    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default="low",
    )

    incident_date = models.DateField()

    action_taken = models.TextField(
        blank=True,
    )

    resolved = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-incident_date", "-id"]
        verbose_name = "Hostel Incident"
        verbose_name_plural = "Hostel Incidents"

    def __str__(self):
        return self.title


# =========================================================
# HOSTEL FEE
# =========================================================

class HostelFee(models.Model):

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="hostel_fees",
    )

    hostel = models.ForeignKey(
        Hostel,
        on_delete=models.CASCADE,
        related_name="fees",
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    due_date = models.DateField()

    paid = models.BooleanField(
        default=False,
    )

    payment_date = models.DateField(
        null=True,
        blank=True,
    )

    reference = models.CharField(
        max_length=100,
        blank=True,
    )

    remarks = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-due_date"]
        verbose_name = "Hostel Fee"
        verbose_name_plural = "Hostel Fees"

    def __str__(self):
        return f"{self.student} - {self.amount}"
# ============================================================
# HOSTEL APPLICATION
# ============================================================

class HostelApplication(models.Model):

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("cancelled", "Cancelled"),
    ]

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="hostel_applications",
    )

    hostel = models.ForeignKey(
        Hostel,
        on_delete=models.CASCADE,
        related_name="applications",
    )

    room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applications",
    )

    requested_date = models.DateField()

    reason = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )

    review_notes = models.TextField(blank=True)

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Hostel Application"
        verbose_name_plural = "Hostel Applications"

    def __str__(self):
        return f"{self.student} - {self.hostel.name} - {self.status}"
