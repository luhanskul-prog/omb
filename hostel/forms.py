from django import forms
from django.apps import apps
from django.core.exceptions import ValidationError

from .models import (
    Hostel,
    Room,
    Bed,
    StudentHostelAllocation,
    HostelAttendance,
    HostelFee,
    HostelIncident,
)

from students.models import Student
from accounts.models import UserProfile


class HostelForm(forms.ModelForm):

    warden_staff = forms.CharField(
        required=False,
        label="Warden / Support Staff",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "id": "id_warden_staff",
                "autocomplete": "off",
                "placeholder": "Type staff name or employee number...",
                "list": "support_staff_list",
            }
        ),
        help_text="Search by support staff name or employee number.",
    )

    class Meta:
        model = Hostel
        fields = [
            "name",
            "hostel_type",
            "location",
            "capacity",
            "warden_staff",
            "warden_name",
            "warden_phone",
            "description",
            "is_active",
        ]

        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "warden_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "id": "id_warden_name",
                    "readonly": "readonly",
                    "placeholder": "Automatically filled from staff",
                }
            ),
            "warden_phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "id": "id_warden_phone",
                    "readonly": "readonly",
                    "placeholder": "Automatically filled from staff",
                }
            ),
        }

    @staticmethod
    def _support_staff_queryset():
        """
        Active STAFF profiles linked to employees but not registered
        as teaching staff.
        """

        qs = (
            UserProfile.objects
            .filter(
                role="STAFF",
                is_active=True,
                employee__isnull=False,
            )
            .select_related(
                "user",
                "employee",
                "custom_role",
                "department",
            )
            .order_by(
                "user__first_name",
                "user__last_name",
            )
        )

        teacher_model = next(
            (
                model
                for model in apps.get_models()
                if model.__name__ == "Teacher"
            ),
            None,
        )

        if teacher_model is not None:
            try:
                teacher_employee_ids = teacher_model.objects.filter(
                    employee_id__isnull=False
                ).values_list("employee_id", flat=True)

                qs = qs.exclude(
                    employee_id__in=teacher_employee_ids
                )
            except Exception:
                pass

        return qs

    @staticmethod
    def _staff_name(profile):
        name = profile.user.get_full_name().strip()

        if not name:
            name = profile.user.username

        return name

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.support_staff = list(
            self._support_staff_queryset()
        )

        self.staff_lookup = {}

        for profile in self.support_staff:

            employee_number = (
                profile.employee_number or ""
            ).strip()

            name = self._staff_name(profile)

            phone = (
                profile.phone or ""
            ).strip()

            record = {
                "employee_number": employee_number,
                "name": name,
                "phone": phone,
            }

            if employee_number:
                self.staff_lookup[
                    employee_number.lower()
                ] = record

            if name:
                self.staff_lookup[
                    name.lower()
                ] = record

        # On edit, identify the existing warden if they are still
        # an active support staff member.
        current_name = (
            self.instance.warden_name or ""
        ).strip()

        current_phone = (
            self.instance.warden_phone or ""
        ).strip()

        for profile in self.support_staff:

            name = self._staff_name(profile)

            phone = (
                profile.phone or ""
            ).strip()

            if (
                current_name
                and name.lower() == current_name.lower()
            ) or (
                current_phone
                and phone
                and phone == current_phone
            ):
                self.initial["warden_staff"] = (
                    profile.employee_number or name
                )
                break

    def clean_warden_staff(self):

        value = (
            self.cleaned_data.get("warden_staff") or ""
        ).strip()

        # Blank means keep existing/manual warden information.
        if not value:
            self.selected_warden = None
            return ""

        staff = self.staff_lookup.get(
            value.lower()
        )

        if staff is None:
            raise forms.ValidationError(
                "Select a valid active support staff member "
                "by name or employee number."
            )

        self.selected_warden = staff

        return staff["employee_number"]

    def clean(self):

        cleaned_data = super().clean()

        selected = getattr(
            self,
            "selected_warden",
            None
        )

        if selected:

            cleaned_data["warden_name"] = (
                selected["name"]
            )

            cleaned_data["warden_phone"] = (
                selected["phone"]
            )

        return cleaned_data
class RoomForm(forms.ModelForm):

    class Meta:
        model = Room
        fields = [
            "hostel",
            "room_number",
            "room_type",
            "capacity",
            "floor",
            "notes",
            "is_active",
        ]

        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class BedForm(forms.ModelForm):

    class Meta:
        model = Bed
        fields = [
            "room",
            "bed_number",
            "status",
            "notes",
        ]

        widgets = {
            "notes": forms.Textarea(attrs={"rows": 2}),
        }


class AllocationForm(forms.ModelForm):

    class Meta:
        model = StudentHostelAllocation
        fields = [
            "student",
            "hostel",
            "room",
            "bed",
            "admission_date",
            "leaving_date",
            "status",
            "remarks",
        ]

        widgets = {
            "admission_date": forms.DateInput(
                attrs={"type": "date"}
            ),
            "leaving_date": forms.DateInput(
                attrs={"type": "date"}
            ),
            "remarks": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["student"].queryset = (
            Student.objects.all().order_by(
                "first_name",
                "last_name"
            )
        )

        self.fields["hostel"].queryset = (
            Hostel.objects.filter(is_active=True)
            .order_by("name")
        )

        self.fields["room"].queryset = (
            Room.objects.filter(is_active=True)
            .select_related("hostel")
            .order_by("hostel__name", "room_number")
        )

        self.fields["bed"].queryset = (
            Bed.objects.select_related(
                "room",
                "room__hostel"
            ).order_by(
                "room__hostel__name",
                "room__room_number",
                "bed_number"
            )
        )

    def clean(self):

        cleaned = super().clean()

        student = cleaned.get("student")
        hostel = cleaned.get("hostel")
        room = cleaned.get("room")
        bed = cleaned.get("bed")
        status = cleaned.get("status")

        if room and hostel and room.hostel_id != hostel.id:
            self.add_error(
                "room",
                "The selected room does not belong to the selected hostel."
            )

        if bed and room and bed.room_id != room.id:
            self.add_error(
                "bed",
                "The selected bed does not belong to the selected room."
            )

        if status == "active" and student:

            qs = StudentHostelAllocation.objects.filter(
                student=student,
                status="active",
            )

            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                self.add_error(
                    "student",
                    "This student already has an active hostel allocation."
                )

        if status == "active" and bed:

            qs = StudentHostelAllocation.objects.filter(
                bed=bed,
                status="active",
            )

            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                self.add_error(
                    "bed",
                    "This bed is already allocated to another student."
                )

        return cleaned


class HostelFeeForm(forms.ModelForm):

    class Meta:
        model = HostelFee
        fields = [
            "student",
            "hostel",
            "amount",
            "due_date",
            "paid",
            "payment_date",
            "reference",
            "remarks",
        ]

        widgets = {
            "due_date": forms.DateInput(
                attrs={"type": "date"}
            ),
            "payment_date": forms.DateInput(
                attrs={"type": "date"}
            ),
            "remarks": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["student"].queryset = (
            Student.objects.all().order_by(
                "first_name",
                "last_name"
            )
        )

        self.fields["hostel"].queryset = (
            Hostel.objects.filter(is_active=True)
            .order_by("name")
        )


class HostelIncidentForm(forms.ModelForm):

    class Meta:
        model = HostelIncident
        fields = [
            "student",
            "hostel",
            "title",
            "description",
            "severity",
            "incident_date",
            "action_taken",
            "resolved",
        ]

        widgets = {
            "incident_date": forms.DateInput(
                attrs={"type": "date"}
            ),
            "description": forms.Textarea(attrs={"rows": 4}),
            "action_taken": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["student"].queryset = (
            Student.objects.all().order_by(
                "first_name",
                "last_name"
            )
        )

        self.fields["hostel"].queryset = (
            Hostel.objects.filter(is_active=True)
            .order_by("name")
        )
