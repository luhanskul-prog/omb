from django.contrib import admin
from .models import (
    Hostel,
    Room,
    Bed,
    StudentHostelAllocation,
    HostelAttendance,
    HostelIncident,
    HostelFee,
)

admin.site.register(Hostel)
admin.site.register(Room)
admin.site.register(Bed)
admin.site.register(StudentHostelAllocation)
admin.site.register(HostelAttendance)
admin.site.register(HostelIncident)
admin.site.register(HostelFee)
