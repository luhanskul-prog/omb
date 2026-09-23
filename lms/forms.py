from django import forms

from .models import (
    LearningResource,
    DigitalLesson,
    Assignment,
    AssignmentSubmission,
    Subject,
    Course,
    CourseClass,
)


# =========================================================
# SUBJECT FORM
# =========================================================

class SubjectForm(forms.ModelForm):

    class Meta:
        model = Subject

        fields = [
            "name",
            "code",
            "description",
            "is_active",
        ]

        widgets = {

            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Mathematics",
                }
            ),

            "code": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. MAT",
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Describe the subject.",
                }
            ),

            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

    def clean_name(self):

        name = self.cleaned_data.get("name")

        if name:
            name = name.strip()

        return name

    def clean_code(self):

        code = self.cleaned_data.get("code")

        if code:
            code = code.strip().upper()

        return code


# =========================================================
# COURSE FORM
# =========================================================

class CourseForm(forms.ModelForm):

    class Meta:
        model = Course

        fields = [
            "title",
            "subject",
            "description",
            "is_published",
        ]

        widgets = {

            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Grade 7 Mathematics",
                }
            ),

            "subject": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": (
                        "Describe what learners will study "
                        "in this course."
                    ),
                }
            ),

            "is_published": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

    def clean_title(self):

        title = self.cleaned_data.get("title")

        if title:
            title = title.strip()

        return title


# =========================================================
# COURSE CLASS FORM
# =========================================================

class CourseClassForm(forms.ModelForm):

    class Meta:
        model = CourseClass

        fields = [
            "course",
            "class_name",
            "stream",
            "is_active",
        ]

        widgets = {

            "course": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "class_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Grade 7",
                }
            ),

            "stream": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. BLUE",
                }
            ),

            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

    def clean_class_name(self):

        class_name = self.cleaned_data.get("class_name")

        if class_name:
            class_name = class_name.strip()

        return class_name

    def clean_stream(self):

        stream = self.cleaned_data.get("stream")

        if stream:
            stream = stream.strip().upper()

        return stream


# =========================================================
# LEARNING RESOURCE FORM
# =========================================================

class LearningResourceForm(forms.ModelForm):

    class Meta:
        model = LearningResource

        fields = [
            "title",
            "description",
            "resource_type",
            "file",
            "external_url",
            "subject",
            "class_name",
            "is_published",
        ]

        widgets = {

            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Resource title",
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Describe this resource",
                }
            ),

            "resource_type": forms.Select(
                attrs={
                    "class": "form-select",
                    "id": "id_resource_type",
                }
            ),

            "file": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "external_url": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://example.com",
                }
            ),

            "subject": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Mathematics",
                }
            ),

            "class_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Grade 7",
                }
            ),

            "is_published": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

    def clean(self):

        cleaned_data = super().clean()

        resource_type = cleaned_data.get(
            "resource_type"
        )

        uploaded_file = cleaned_data.get(
            "file"
        )

        external_url = cleaned_data.get(
            "external_url"
        )

        if resource_type in [
            "DOCUMENT",
            "VIDEO",
        ]:

            if not uploaded_file:

                if (
                    not self.instance.pk
                    or not self.instance.file
                ):

                    self.add_error(
                        "file",
                        "Please upload a file for this resource."
                    )

        if resource_type == "LINK":

            if not external_url:

                self.add_error(
                    "external_url",
                    "Please enter an external URL."
                )

        return cleaned_data


# =========================================================
# DIGITAL LESSON FORM
# =========================================================

class DigitalLessonForm(forms.ModelForm):

    class Meta:
        model = DigitalLesson

        fields = [
            "title",
            "subject",
            "class_name",
            "description",
            "content",
            "video_url",
            "attachment",
            "is_published",
        ]

        widgets = {

            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "e.g. Introduction to Algebra"
                    ),
                }
            ),

            "subject": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Mathematics",
                }
            ),

            "class_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Grade 7",
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": (
                        "Briefly describe what learners "
                        "will learn in this lesson."
                    ),
                }
            ),

            "content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 10,
                    "placeholder": (
                        "Enter the lesson content, notes, "
                        "instructions or learning activities."
                    ),
                }
            ),

            "video_url": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "https://www.youtube.com/..."
                    ),
                }
            ),

            "attachment": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "is_published": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

    def clean(self):

        cleaned_data = super().clean()

        content = cleaned_data.get(
            "content"
        )

        video_url = cleaned_data.get(
            "video_url"
        )

        attachment = cleaned_data.get(
            "attachment"
        )

        if (
            not content
            and not video_url
            and not attachment
        ):

            raise forms.ValidationError(
                "Please provide lesson content, "
                "a video URL, or an attachment."
            )

        return cleaned_data


# =========================================================
# ASSIGNMENT FORM
# =========================================================

class AssignmentForm(forms.ModelForm):

    class Meta:
        model = Assignment

        fields = [
            "title",
            "subject",
            "class_name",
            "description",
            "instructions",
            "attachment",
            "due_date",
            "total_marks",
            "is_published",
        ]

        widgets = {

            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "e.g. Algebra Assignment 1"
                    ),
                }
            ),

            "subject": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Mathematics",
                }
            ),

            "class_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Grade 7",
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": (
                        "Briefly describe the assignment."
                    ),
                }
            ),

            "instructions": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 7,
                    "placeholder": (
                        "Enter the instructions learners "
                        "should follow."
                    ),
                }
            ),

            "attachment": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "due_date": forms.DateTimeInput(
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                }
            ),

            "total_marks": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                    "placeholder": "e.g. 100",
                }
            ),

            "is_published": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

    def clean_total_marks(self):

        total_marks = self.cleaned_data.get(
            "total_marks"
        )

        if (
            total_marks is not None
            and total_marks < 1
        ):

            raise forms.ValidationError(
                "Total marks must be at least 1."
            )

        return total_marks


# =========================================================
# ASSIGNMENT SUBMISSION FORM
# =========================================================

class AssignmentSubmissionForm(forms.ModelForm):

    class Meta:
        model = AssignmentSubmission

        fields = [
            "answer",
            "attachment",
        ]

        widgets = {

            "answer": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 10,
                    "placeholder": (
                        "Enter your answer here..."
                    ),
                }
            ),

            "attachment": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                }
            ),
        }

    def clean(self):

        cleaned_data = super().clean()

        answer = cleaned_data.get(
            "answer"
        )

        attachment = cleaned_data.get(
            "attachment"
        )

        if not answer and not attachment:

            raise forms.ValidationError(
                "Please provide an answer or upload "
                "a file before submitting."
            )

        return cleaned_data


# =========================================================
# ASSIGNMENT MARKING FORM
# =========================================================

class AssignmentMarkForm(forms.ModelForm):

    class Meta:
        model = AssignmentSubmission

        fields = [
            "marks",
            "feedback",
            "status",
        ]

        widgets = {

            "marks": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "placeholder": "Enter marks",
                }
            ),

            "feedback": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": (
                        "Enter feedback for the learner."
                    ),
                }
            ),

            "status": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
        }

    def clean_marks(self):

        marks = self.cleaned_data.get(
            "marks"
        )

        if marks is not None and marks < 0:

            raise forms.ValidationError(
                "Marks cannot be negative."
            )

        return marks