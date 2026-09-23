from django.shortcuts import render
from django.db.models import Q
from students.models import Student
from academic.models import Assessment
from fees.models import FeeRecord
from attendance.models import Attendance
from timetable.legacy_compat import TimetableEntry
from noticeboard.models import Notice

def student_dashboard_view(request):
    # Fetch Aggrey Onyango as our default student for the portal demo
    student = Student.objects.first()
    
    context = {
        'student': student,
        'assessments': Assessment.objects.filter(student=student).select_related('subject', 'assessment_type')[:10],
        'fee_records': FeeRecord.objects.filter(student=student),
        'attendance_records': Attendance.objects.filter(student=student)[:10],
        'notices': Notice.objects.filter(published=True).filter(
            Q(audience='everyone') | Q(audience='students')
        )[:5],
        'timetable': TimetableEntry.objects.filter(
            class_name=student.class_name, 
            stream=student.stream
        ).select_related('subject', 'day', 'period', 'room')
    }
    return render(request, 'student/dashboard.html', context)

