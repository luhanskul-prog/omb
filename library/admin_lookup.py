from django.http import JsonResponse

from students.models import Student
from hr_payroll.models import Employee


def lookup_member(request):
    member_type = request.GET.get("member_type", "").strip()
    number = request.GET.get("number", "").strip()

    if not number:
        return JsonResponse({
            "success": False,
            "message": "Enter a number."
        })

    if member_type == "student":

        try:
            student = Student.objects.get(
                admission_no__iexact=number
            )
        except Student.DoesNotExist:
            return JsonResponse({
                "success": False,
                "message": f"No student found with admission number '{number}'."
            })

        name = " ".join(
            x for x in [
                student.first_name,
                student.middle_name,
                student.last_name,
            ]
            if x
        )

        return JsonResponse({
            "success": True,
            "member_type": "student",
            "name": name,
            "number": student.admission_no,
            "class_name": student.class_name or "",
            "stream": student.stream or "",
            "phone": student.parent_phone or "",
            "email": "",
            "details": (
                f"Name: {name}\n"
                f"Admission Number: {student.admission_no}\n"
                f"Class: {student.class_name or '-'}\n"
                f"Stream: {student.stream or '-'}\n"
                f"Parent Phone: {student.parent_phone or '-'}"
            ),
        })

    if member_type == "staff":

        try:
            employee = Employee.objects.get(
                employee_number__iexact=number
            )
        except Employee.DoesNotExist:
            return JsonResponse({
                "success": False,
                "message": f"No employee found with employee number '{number}'."
            })

        name = " ".join(
            x for x in [
                employee.first_name,
                employee.middle_name,
                employee.last_name,
            ]
            if x
        )

        return JsonResponse({
            "success": True,
            "member_type": "staff",
            "name": name,
            "number": employee.employee_number or "",
            "job_title": str(employee.position or ""),
            "department": str(employee.department or ""),
            "phone": employee.phone or "",
            "email": employee.email or "",
            "details": (
                f"Name: {name}\n"
                f"Employee Number: {employee.employee_number or '-'}\n"
                f"Job Title: {employee.position or '-'}\n"
                f"Department: {employee.department or '-'}\n"
                f"Phone: {employee.phone or '-'}"
            ),
        })

    return JsonResponse({
        "success": False,
        "message": "Select Student or Staff."
    })