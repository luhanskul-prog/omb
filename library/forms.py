from django import forms

from students.models import Student
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import (
    Category,
    Book,
    LibraryMember,
    BookIssue,
)


class StyledModelForm(forms.ModelForm):

    class Meta:
        fields = "__all__"

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():

            if isinstance(
                field.widget,
                forms.CheckboxInput
            ):

                field.widget.attrs.update({
                    "class": "form-check-input"
                })

            else:

                field.widget.attrs.update({
                    "class": "form-control"
                })


class CategoryForm(StyledModelForm):

    class Meta:
        model = Category
        fields = "__all__"


class BookForm(StyledModelForm):

    class Meta:
        model = Book
        fields = "__all__"

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        if "isbn" in self.fields:

            self.fields["isbn"].required = False

            self.fields["isbn"].widget = forms.HiddenInput()


class LibraryMemberForm(StyledModelForm):

    class Meta:
        model = LibraryMember
        fields = "__all__"


class LibraryMemberLookupForm(forms.Form):

    MEMBER_TYPE_CHOICES = [
        ("student", "Student"),
        ("staff", "Staff"),
    ]

    member_type = forms.ChoiceField(
        choices=MEMBER_TYPE_CHOICES,
        widget=forms.Select(
            attrs={
                "class": "form-control",
                "id": "member_type",
            }
        )
    )

    identifier = forms.CharField(
        label="Admission Number / Employee Number",
        max_length=50,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "id": "member_identifier",
                "placeholder":
                    "Enter admission number or employee number",
                "autocomplete": "off",
            }
        )
    )


class LibraryIssueCreateForm(forms.ModelForm):

    class Meta:
        model = BookIssue
        fields = [
            "book",
            "member",
            "issue_date",
            "due_date",
            "notes",
        ]

        widgets = {
            "issue_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                }
            ),
            "due_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields["book"].queryset = (
            Book.objects
            .filter(available_copies__gt=0)
            .order_by("title")
        )

        self.fields["book"].widget.attrs.update({
            "class": "form-control",
        })

        for book in self.fields["book"].queryset:
            self.fields["book"].widget.choices.queryset = self.fields["book"].queryset
            break
        self.fields["member"].queryset = (
            LibraryMember.objects
            .filter(active=True)
            .select_related(
                "student",
                "employee",
            )
            .order_by("name")
        )

    def clean(self):

        cleaned = super().clean()

        issue_date = cleaned.get("issue_date")
        due_date = cleaned.get("due_date")

        if issue_date and due_date:

            if due_date < issue_date:

                self.add_error(
                    "due_date",
                    "Due date cannot be earlier than issue date."
                )

        return cleaned


class LibraryIssueEditForm(forms.ModelForm):

    class Meta:
        model = BookIssue
        fields = [
            "book",
            "member",
            "issue_date",
            "due_date",
            "status",
            "notes",
        ]

        widgets = {
            "issue_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                }
            ),
            "due_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                }
            ),
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields["book"].queryset = (
            Book.objects
            .all()
            .order_by("title")
        )

        self.fields["member"].queryset = (
            LibraryMember.objects
            .all()
            .select_related(
                "student",
                "employee",
            )
            .order_by("name")
        )

    def clean(self):

        cleaned = super().clean()

        issue_date = cleaned.get("issue_date")
        due_date = cleaned.get("due_date")

        if issue_date and due_date:

            if due_date < issue_date:

                self.add_error(
                    "due_date",
                    "Due date cannot be earlier than issue date."
                )

        return cleaned


class BookIssueForm(StyledModelForm):

    class Meta:
        model = BookIssue
        fields = "__all__"


