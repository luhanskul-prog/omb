from django.contrib.auth.decorators import login_required
from accounts.staff_access import (
    role_permission_required,
    is_class_teacher_for,
    can_enter_marks,
)
from accounts.views import user_has_role_permission
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import (
    render,
    redirect,
    get_object_or_404,
)

from .models import (
    Subject,
    Course,
    CourseClass,
    LearningResource,
    DigitalLesson,
    Assignment,
    AssignmentSubmission,
)

from .forms import (
    LearningResourceForm,
    DigitalLessonForm,
    AssignmentForm,
    AssignmentSubmissionForm,
    AssignmentMarkForm,
    SubjectForm,
    CourseForm,
    CourseClassForm,
)


# =========================================================
# LMS DASHBOARD
# =========================================================

@login_required
@role_permission_required("view_learningresource", "lms")
def lms_dashboard(request):

    context = {
        "resources_count": LearningResource.objects.filter(
            is_published=True
        ).count(),

        "documents_count": LearningResource.objects.filter(
            resource_type="DOCUMENT",
            is_published=True
        ).count(),

        "videos_count": LearningResource.objects.filter(
            resource_type="VIDEO",
            is_published=True
        ).count(),

        "links_count": LearningResource.objects.filter(
            resource_type="LINK",
            is_published=True
        ).count(),

        "lessons_count": DigitalLesson.objects.filter(
            is_published=True
        ).count(),

        "assignments_count": Assignment.objects.filter(
            is_published=True
        ).count(),

        "courses_count": Course.objects.filter(
            is_published=True
        ).count(),

        "subjects_count": Subject.objects.filter(
            is_active=True
        ).count(),

        "classes_count": CourseClass.objects.filter(
            is_active=True
        ).count(),
    }

    return render(
        request,
        "lms/dashboard.html",
        context
    )


# =========================================================
# LEARNING RESOURCES DASHBOARD
# =========================================================

@login_required
@role_permission_required("view_learningresource", "lms")
def resources(request):

    context = {
        "documents_count": LearningResource.objects.filter(
            resource_type="DOCUMENT"
        ).count(),

        "videos_count": LearningResource.objects.filter(
            resource_type="VIDEO"
        ).count(),

        "links_count": LearningResource.objects.filter(
            resource_type="LINK"
        ).count(),
    }

    return render(
        request,
        "lms/resources.html",
        context
    )


# =========================================================
# NOTES & DOCUMENTS
# =========================================================

@login_required
@role_permission_required("view_learningresource", "lms")
def resource_documents(request):

    resources = LearningResource.objects.filter(
        resource_type="DOCUMENT"
    )

    return render(
        request,
        "lms/resource_documents.html",
        {
            "resources": resources,
            "resource_type": "DOCUMENT",
            "page_title": "Notes & Documents",
        }
    )


# =========================================================
# VIDEOS
# =========================================================

@login_required
@role_permission_required("view_learningresource", "lms")
def resource_videos(request):

    resources = LearningResource.objects.filter(
        resource_type="VIDEO"
    )

    return render(
        request,
        "lms/resource_videos.html",
        {
            "resources": resources,
            "resource_type": "VIDEO",
            "page_title": "Educational Videos",
        }
    )


# =========================================================
# EXTERNAL LINKS
# =========================================================

@login_required
@role_permission_required("view_learningresource", "lms")
def resource_links(request):

    resources = LearningResource.objects.filter(
        resource_type="LINK"
    )

    return render(
        request,
        "lms/resource_links.html",
        {
            "resources": resources,
            "resource_type": "LINK",
            "page_title": "External Learning Links",
        }
    )


# =========================================================
# ADD RESOURCE
# =========================================================

@login_required
@role_permission_required("add_learningresource", "lms")
def resource_create(request):

    if request.method == "POST":

        form = LearningResourceForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            resource = form.save(
                commit=False
            )

            resource.uploaded_by = request.user
            resource.save()

            messages.success(
                request,
                "Learning resource added successfully."
            )

            return redirect(
                "lms:resources"
            )

    else:

        form = LearningResourceForm()

    return render(
        request,
        "lms/resource_form.html",
        {
            "form": form,
            "page_title": "Add Learning Resource",
        }
    )


# =========================================================
# DELETE RESOURCE
# =========================================================

@login_required
@role_permission_required("delete_learningresource", "lms")
def resource_delete(request, pk):

    resource = get_object_or_404(
        LearningResource,
        pk=pk
    )

    if request.method == "POST":

        resource.delete()

        messages.success(
            request,
            "Learning resource deleted successfully."
        )

        return redirect(
            "lms:resources"
        )

    return render(
        request,
        "lms/resource_confirm_delete.html",
        {
            "resource": resource
        }
    )


# =========================================================
# DIGITAL LESSONS DASHBOARD
# =========================================================

@login_required
@role_permission_required("view_digitallesson", "lms")
def lessons(request):

    lessons = DigitalLesson.objects.all()

    context = {
        "lessons_count": lessons.count(),

        "my_lessons_count": lessons.filter(
            created_by=request.user
        ).count(),

        "published_lessons_count": lessons.filter(
            is_published=True
        ).count(),
    }

    return render(
        request,
        "lms/lessons.html",
        context
    )


# =========================================================
# CREATE DIGITAL LESSON
# =========================================================

@login_required
@role_permission_required("add_digitallesson", "lms")
def lesson_create(request):

    if request.method == "POST":

        form = DigitalLessonForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            lesson = form.save(
                commit=False
            )

            lesson.created_by = request.user
            lesson.save()

            messages.success(
                request,
                "Digital lesson created successfully."
            )

            return redirect(
                "lms:my_lessons"
            )

    else:

        form = DigitalLessonForm()

    return render(
        request,
        "lms/lesson_form.html",
        {
            "form": form,
            "page_title": "Create Digital Lesson",
            "button_text": "Create Lesson",
        }
    )


# =========================================================
# MY LESSONS
# =========================================================

@login_required
@role_permission_required("view_digitallesson", "lms")
def my_lessons(request):

    lessons = DigitalLesson.objects.filter(
        created_by=request.user
    )

    return render(
        request,
        "lms/my_lessons.html",
        {
            "lessons": lessons,
            "page_title": "My Lessons",
        }
    )


# =========================================================
# LEARNER LESSONS
# =========================================================

@login_required
def learner_lessons(request):

    profile = getattr(request.user, "profile", None)

    if profile is None:
        messages.error(
            request,
            "Your account is not authorized to access learner lessons.",
        )
        return redirect("accounts:login")

    role = str(
        getattr(profile, "role", "") or ""
    ).upper()

    # Students see published lessons for their own class
    # plus general lessons with no class specified.
    if role == "STUDENT":

        student = getattr(profile, "student", None)

        if student is None:
            messages.error(
                request,
                "Your account is not linked to a student record.",
            )
            return redirect("accounts:student_dashboard")

        class_name = str(
            getattr(student, "class_name", "") or ""
        ).strip()

        lessons = DigitalLesson.objects.filter(
            is_published=True
        ).filter(
            Q(class_name="") |
            Q(class_name__iexact=class_name)
        )

    # Parents see published lessons relevant to at least
    # one of their children, plus general lessons.
    elif role == "PARENT":

        parent = getattr(request.user, "parent", None)

        if parent is None:
            messages.error(
                request,
                "Your account is not linked to a parent profile.",
            )
            return redirect("accounts:parent_dashboard")

        child_classes = list(
            parent.children
            .exclude(class_name="")
            .values_list("class_name", flat=True)
        )

        lessons = DigitalLesson.objects.filter(
            is_published=True
        ).filter(
            Q(class_name="") |
            Q(class_name__in=child_classes)
        )

    # Staff/admin users with the LMS view permission can
    # retain the existing lesson-detail access.
    elif user_has_role_permission(
        request.user,
        "view_digitallesson",
        "lms",
    ):

        lessons = DigitalLesson.objects.filter(
            is_published=True
        )

    else:
        messages.error(
            request,
            "You do not have permission to access learner lessons.",
        )
        return redirect("accounts:staff_dashboard")

    return render(
        request,
        "lms/learner_lessons.html",
        {
            "lessons": lessons,
            "page_title": "Learner Lessons",
        }
    )


# =========================================================
# EDIT DIGITAL LESSON
# =========================================================

@login_required
@role_permission_required("change_digitallesson", "lms")
def lesson_edit(request, pk):

    lesson = get_object_or_404(
        DigitalLesson,
        pk=pk
    )

    if request.method == "POST":

        form = DigitalLessonForm(
            request.POST,
            request.FILES,
            instance=lesson
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Digital lesson updated successfully."
            )

            return redirect(
                "lms:my_lessons"
            )

    else:

        form = DigitalLessonForm(
            instance=lesson
        )

    return render(
        request,
        "lms/lesson_form.html",
        {
            "form": form,
            "lesson": lesson,
            "page_title": "Edit Digital Lesson",
            "button_text": "Update Lesson",
        }
    )


# =========================================================
# DELETE DIGITAL LESSON
# =========================================================

@login_required
@role_permission_required("delete_digitallesson", "lms")
def lesson_delete(request, pk):

    lesson = get_object_or_404(
        DigitalLesson,
        pk=pk
    )

    if request.method == "POST":

        lesson.delete()

        messages.success(
            request,
            "Digital lesson deleted successfully."
        )

        return redirect(
            "lms:my_lessons"
        )

    return render(
        request,
        "lms/lesson_confirm_delete.html",
        {
            "lesson": lesson
        }
    )


# =========================================================
# VIEW DIGITAL LESSON
# =========================================================

@login_required
def lesson_detail(request, pk):

    profile = getattr(request.user, "profile", None)

    if profile is None:
        messages.error(
            request,
            "Your account is not authorized to view this lesson.",
        )
        return redirect("accounts:login")

    role = str(
        getattr(profile, "role", "") or ""
    ).upper()

    # -----------------------------------------------------
    # STUDENT ACCESS
    # -----------------------------------------------------

    if role == "STUDENT":

        student = getattr(profile, "student", None)

        if student is None:
            messages.error(
                request,
                "Your account is not linked to a student record.",
            )
            return redirect("accounts:student_dashboard")

        class_name = str(
            getattr(student, "class_name", "") or ""
        ).strip()

        lesson = get_object_or_404(
            DigitalLesson.objects.filter(
                is_published=True
            ).filter(
                Q(class_name="") |
                Q(class_name__iexact=class_name)
            ),
            pk=pk,
        )

    # -----------------------------------------------------
    # PARENT ACCESS
    # -----------------------------------------------------

    elif role == "PARENT":

        parent = getattr(request.user, "parent", None)

        if parent is None:
            messages.error(
                request,
                "Your account is not linked to a parent profile.",
            )
            return redirect("accounts:parent_dashboard")

        child_classes = list(
            parent.children
            .exclude(class_name="")
            .values_list("class_name", flat=True)
        )

        class_query = Q(class_name="")

        for child_class in child_classes:
            class_query |= Q(
                class_name__iexact=str(child_class).strip()
            )

        lesson = get_object_or_404(
            DigitalLesson.objects.filter(
                is_published=True
            ).filter(class_query),
            pk=pk,
        )

    # -----------------------------------------------------
    # STAFF / ADMIN ACCESS
    # -----------------------------------------------------

    elif user_has_role_permission(
        request.user,
        "view_digitallesson",
        "lms",
    ):

        lesson = get_object_or_404(
            DigitalLesson,
            pk=pk,
            is_published=True,
        )

    else:
        messages.error(
            request,
            "You do not have permission to view this lesson.",
        )
        return redirect("accounts:staff_dashboard")

    return render(
        request,
        "lms/lesson_detail.html",
        {
            "lesson": lesson
        }
    )


# =========================================================
# ASSIGNMENTS DASHBOARD
# =========================================================

@login_required
@role_permission_required("view_assignment", "lms")
def assignments(request):

    assignments = Assignment.objects.all()

    context = {
        "assignments_count": assignments.count(),

        "my_assignments_count": assignments.filter(
            created_by=request.user
        ).count(),

        "published_assignments_count": assignments.filter(
            is_published=True
        ).count(),
    }

    return render(
        request,
        "lms/assignments.html",
        context
    )


# =========================================================
# CREATE ASSIGNMENT
# =========================================================

@login_required
@role_permission_required("add_assignment", "lms")
def assignment_create(request):

    if request.method == "POST":

        form = AssignmentForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            assignment = form.save(
                commit=False
            )

            assignment.created_by = request.user
            assignment.save()

            messages.success(
                request,
                "Assignment created successfully."
            )

            return redirect(
                "lms:my_assignments"
            )

    else:

        form = AssignmentForm()

    return render(
        request,
        "lms/assignment_form.html",
        {
            "form": form,
            "page_title": "Create Assignment",
            "button_text": "Create Assignment",
        }
    )


# =========================================================
# MY ASSIGNMENTS
# =========================================================

@login_required
@role_permission_required("view_assignment", "lms")
def my_assignments(request):

    assignments = Assignment.objects.filter(
        created_by=request.user
    )

    return render(
        request,
        "lms/my_assignments.html",
        {
            "assignments": assignments,
            "page_title": "My Assignments",
        }
    )


# =========================================================
# LEARNER ASSIGNMENTS
# =========================================================

@login_required
def learner_assignments(request):

    profile = getattr(request.user, "profile", None)

    if profile is None:
        messages.error(
            request,
            "Your account is not authorized to access learner assignments.",
        )
        return redirect("accounts:login")

    role = str(
        getattr(profile, "role", "") or ""
    ).upper()

    # -----------------------------------------------------
    # STUDENT ACCESS
    # -----------------------------------------------------

    if role == "STUDENT":

        student = getattr(profile, "student", None)

        if student is None:
            messages.error(
                request,
                "Your account is not linked to a student record.",
            )
            return redirect("accounts:student_dashboard")

        class_name = str(
            getattr(student, "class_name", "") or ""
        ).strip()

        assignments = Assignment.objects.filter(
            is_published=True
        ).filter(
            Q(class_name="") |
            Q(class_name__iexact=class_name)
        )

    # -----------------------------------------------------
    # PARENT ACCESS
    # -----------------------------------------------------

    elif role == "PARENT":

        parent = getattr(request.user, "parent", None)

        if parent is None:
            messages.error(
                request,
                "Your account is not linked to a parent profile.",
            )
            return redirect("accounts:parent_dashboard")

        child_classes = list(
            parent.children
            .exclude(class_name="")
            .values_list("class_name", flat=True)
        )

        class_query = Q(class_name="")

        for child_class in child_classes:
            class_query |= Q(
                class_name__iexact=str(child_class).strip()
            )

        assignments = Assignment.objects.filter(
            is_published=True
        ).filter(class_query)

    # -----------------------------------------------------
    # STAFF / ADMIN ACCESS
    # -----------------------------------------------------

    elif user_has_role_permission(
        request.user,
        "view_assignment",
        "lms",
    ):

        assignments = Assignment.objects.filter(
            is_published=True
        )

    else:
        messages.error(
            request,
            "You do not have permission to access learner assignments.",
        )
        return redirect("accounts:staff_dashboard")

    return render(
        request,
        "lms/learner_assignments.html",
        {
            "assignments": assignments,
            "page_title": "Learner Assignments",
        }
    )


# =========================================================
# EDIT ASSIGNMENT
# =========================================================

@login_required
@role_permission_required("change_assignment", "lms")
def assignment_edit(request, pk):

    assignment = get_object_or_404(
        Assignment,
        pk=pk
    )

    if request.method == "POST":

        form = AssignmentForm(
            request.POST,
            request.FILES,
            instance=assignment
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Assignment updated successfully."
            )

            return redirect(
                "lms:my_assignments"
            )

    else:

        form = AssignmentForm(
            instance=assignment
        )

    return render(
        request,
        "lms/assignment_form.html",
        {
            "form": form,
            "assignment": assignment,
            "page_title": "Edit Assignment",
            "button_text": "Update Assignment",
        }
    )


# =========================================================
# DELETE ASSIGNMENT
# =========================================================

@login_required
@role_permission_required("delete_assignment", "lms")
def assignment_delete(request, pk):

    assignment = get_object_or_404(
        Assignment,
        pk=pk
    )

    if request.method == "POST":

        assignment.delete()

        messages.success(
            request,
            "Assignment deleted successfully."
        )

        return redirect(
            "lms:my_assignments"
        )

    return render(
        request,
        "lms/assignment_confirm_delete.html",
        {
            "assignment": assignment
        }
    )


# =========================================================
# ASSIGNMENT DETAIL
# =========================================================

@login_required
def assignment_detail(request, pk):

    profile = getattr(request.user, "profile", None)

    if profile is None:
        messages.error(
            request,
            "Your account is not authorized to view this assignment.",
        )
        return redirect("accounts:login")

    role = str(
        getattr(profile, "role", "") or ""
    ).upper()

    # -----------------------------------------------------
    # STUDENT ACCESS
    # -----------------------------------------------------

    if role == "STUDENT":

        student = getattr(profile, "student", None)

        if student is None:
            messages.error(
                request,
                "Your account is not linked to a student record.",
            )
            return redirect("accounts:student_dashboard")

        class_name = str(
            getattr(student, "class_name", "") or ""
        ).strip()

        assignment = get_object_or_404(
            Assignment.objects.filter(
                is_published=True
            ).filter(
                Q(class_name="") |
                Q(class_name__iexact=class_name)
            ),
            pk=pk,
        )

    # -----------------------------------------------------
    # PARENT ACCESS
    # -----------------------------------------------------

    elif role == "PARENT":

        parent = getattr(request.user, "parent", None)

        if parent is None:
            messages.error(
                request,
                "Your account is not linked to a parent profile.",
            )
            return redirect("accounts:parent_dashboard")

        child_classes = list(
            parent.children
            .exclude(class_name="")
            .values_list("class_name", flat=True)
        )

        class_query = Q(class_name="")

        for child_class in child_classes:
            class_query |= Q(
                class_name__iexact=str(child_class).strip()
            )

        assignment = get_object_or_404(
            Assignment.objects.filter(
                is_published=True
            ).filter(class_query),
            pk=pk,
        )

    # -----------------------------------------------------
    # STAFF / ADMIN ACCESS
    # -----------------------------------------------------

    elif user_has_role_permission(
        request.user,
        "view_assignment",
        "lms",
    ):

        assignment = get_object_or_404(
            Assignment,
            pk=pk,
            is_published=True,
        )

    else:
        messages.error(
            request,
            "You do not have permission to view this assignment.",
        )
        return redirect("accounts:staff_dashboard")

    return render(
        request,
        "lms/assignment_detail.html",
        {
            "assignment": assignment
        }
    )


# =========================================================
# SUBMIT ASSIGNMENT
# =========================================================

@login_required
def assignment_submit(request, pk):

    profile = getattr(request.user, "profile", None)

    if profile is None:
        messages.error(
            request,
            "Your account is not authorized to submit assignments.",
        )
        return redirect("accounts:login")

    role = str(
        getattr(profile, "role", "") or ""
    ).upper()

    # -----------------------------------------------------
    # STUDENT
    # -----------------------------------------------------

    if role == "STUDENT":

        student = getattr(profile, "student", None)

        if student is None:
            messages.error(
                request,
                "Your account is not linked to a student record.",
            )
            return redirect("accounts:student_dashboard")

        class_name = str(
            getattr(student, "class_name", "") or ""
        ).strip()

        assignment = get_object_or_404(
            Assignment.objects.filter(
                is_published=True
            ).filter(
                Q(class_name="") |
                Q(class_name__iexact=class_name)
            ),
            pk=pk,
        )

    # -----------------------------------------------------
    # PARENT
    # Parents may view learner assignments, but cannot submit.
    # -----------------------------------------------------

    elif role == "PARENT":

        messages.error(
            request,
            "Parent accounts can view assignments but cannot submit learner work.",
        )
        return redirect("accounts:parent_dashboard")

    else:
        messages.error(
            request,
            "Only student accounts may submit assignments.",
        )
        return redirect("accounts:staff_dashboard")

    existing_submission = AssignmentSubmission.objects.filter(
        assignment=assignment,
        learner=request.user
    ).first()

    if request.method == "POST":

        if existing_submission:

            form = AssignmentSubmissionForm(
                request.POST,
                request.FILES,
                instance=existing_submission
            )

        else:

            form = AssignmentSubmissionForm(
                request.POST,
                request.FILES
            )

        if form.is_valid():

            submission = form.save(
                commit=False
            )

            submission.assignment = assignment
            submission.learner = request.user
            submission.status = "SUBMITTED"
            submission.save()

            messages.success(
                request,
                "Assignment submitted successfully."
            )

            return redirect(
                "lms:learner_assignments"
            )

    else:

        if existing_submission:

            form = AssignmentSubmissionForm(
                instance=existing_submission
            )

        else:

            form = AssignmentSubmissionForm()

    return render(
        request,
        "lms/assignment_submit.html",
        {
            "form": form,
            "assignment": assignment,
            "page_title": "Submit Assignment",
        }
    )



# =========================================================
# LMS TEACHER ASSIGNMENT ACCESS
# =========================================================

def _teacher_can_access_assignment(user, assignment):
    """
    Check whether a teacher is authorized for an assignment.

    Class teachers may access all subjects in their assigned class.
    Subject teachers may access only their assigned subject/class.
    Administrators are allowed.
    """

    if user.is_superuser:
        return True

    profile = getattr(user, "profile", None)

    if profile is None:
        return False

    role = str(
        getattr(profile, "role", "") or ""
    ).upper()

    if role == "ADMIN":
        return True

    class_name = str(
        getattr(assignment, "class_name", "") or ""
    ).strip()

    subject_name = str(
        getattr(assignment, "subject", "") or ""
    ).strip()

    if not class_name:
        return False

    if is_class_teacher_for(
        user,
        class_name,
        "",
    ):
        return True

    if not subject_name:
        return False

    from academic.models import Subject as AcademicSubject

    academic_subject = AcademicSubject.objects.filter(
        is_active=True,
        name__iexact=subject_name,
    ).first()

    if academic_subject is None:
        return False

    return can_enter_marks(
        user,
        class_name,
        "",
        academic_subject,
    )


# =========================================================
# ASSIGNMENT SUBMISSIONS
# =========================================================

@login_required
@role_permission_required("view_assignmentsubmission", "lms")
def assignment_submissions(request, pk):

    assignment = get_object_or_404(
        Assignment,
        pk=pk
    )

    if not _teacher_can_access_assignment(
        request.user,
        assignment
    ):
        messages.error(
            request,
            "You are not authorized to view submissions for this assignment."
        )
        return redirect("accounts:staff_dashboard")

    submissions = AssignmentSubmission.objects.filter(
        assignment=assignment
    ).select_related(
        "learner"
    )

    return render(
        request,
        "lms/assignment_submissions.html",
        {
            "assignment": assignment,
            "submissions": submissions,
            "page_title": "Assignment Submissions",
        }
    )




# =========================================================
# MARK ASSIGNMENT
# =========================================================

@login_required
@role_permission_required("change_assignmentsubmission", "lms")
def assignment_mark(request, pk):

    submission = get_object_or_404(
        AssignmentSubmission,
        pk=pk
    )

    assignment = submission.assignment

    if not _teacher_can_access_assignment(
        request.user,
        assignment
    ):
        messages.error(
            request,
            "You are not authorized to mark submissions for this assignment."
        )
        return redirect("accounts:staff_dashboard")

    if request.method == "POST":

        form = AssignmentMarkForm(
            request.POST,
            instance=submission
        )

        if form.is_valid():

            submission = form.save(
                commit=False
            )

            submission.status = "MARKED"
            submission.save()

            messages.success(
                request,
                "Assignment marked successfully."
            )

            return redirect(
                "lms:assignment_submissions",
                pk=submission.assignment.pk
            )

    else:

        form = AssignmentMarkForm(
            instance=submission
        )

    return render(
        request,
        "lms/assignment_mark.html",
        {
            "form": form,
            "submission": submission,
            "assignment": assignment,
            "page_title": "Mark Assignment",
        }
    )




# =========================================================
# COURSES DASHBOARD
# =========================================================

@login_required
@role_permission_required("view_course", "lms")
def courses(request):

    context = {
        "courses_count": Course.objects.count(),

        "published_courses_count": Course.objects.filter(
            is_published=True
        ).count(),

        "subjects_count": Subject.objects.filter(
            is_active=True
        ).count(),

        "classes_count": CourseClass.objects.filter(
            is_active=True
        ).count(),
    }

    return render(
        request,
        "lms/courses.html",
        context
    )


# =========================================================
# CREATE COURSE
# =========================================================

@login_required
@role_permission_required("add_course", "lms")
def course_create(request):

    if request.method == "POST":

        form = CourseForm(
            request.POST
        )

        if form.is_valid():

            course = form.save(
                commit=False
            )

            course.created_by = request.user
            course.save()

            messages.success(
                request,
                "Course created successfully."
            )

            return redirect(
                "lms:course_list"
            )

    else:

        form = CourseForm()

    return render(
        request,
        "lms/course_form.html",
        {
            "form": form,
            "page_title": "Create Course",
            "button_text": "Create Course",
        }
    )


# =========================================================
# COURSE LIST
# =========================================================

@login_required
@role_permission_required("view_course", "lms")
def course_list(request):

    courses = Course.objects.select_related(
        "subject",
        "created_by"
    ).prefetch_related(
        "classes"
    )

    return render(
        request,
        "lms/course_list.html",
        {
            "courses": courses,
            "page_title": "Courses",
        }
    )


# =========================================================
# COURSE DETAIL
# =========================================================

@login_required
@role_permission_required("view_course", "lms")
def course_detail(request, pk):

    course = get_object_or_404(
        Course.objects.select_related(
            "subject",
            "created_by"
        ).prefetch_related(
            "classes"
        ),
        pk=pk
    )

    return render(
        request,
        "lms/course_detail.html",
        {
            "course": course,
            "page_title": course.title,
        }
    )


# =========================================================
# SUBJECT LIST
# =========================================================

@login_required
@role_permission_required("view_subject", "lms")
def subject_list(request):

    subjects = Subject.objects.prefetch_related(
        "courses"
    )

    return render(
        request,
        "lms/subject_list.html",
        {
            "subjects": subjects,
            "page_title": "Subjects",
        }
    )


# =========================================================
# CLASS LIST
# =========================================================

@login_required
@role_permission_required("view_courseclass", "lms")
def course_class_list(request):

    course_classes = CourseClass.objects.select_related(
        "course",
        "course__subject"
    )

    return render(
        request,
        "lms/course_class_list.html",
        {
            "course_classes": course_classes,
            "page_title": "Classes",
        }
    )