from django.urls import path

from . import views


app_name = "lms"


urlpatterns = [

    # =========================================================
    # LMS DASHBOARD
    # =========================================================

    path(
        "",
        views.lms_dashboard,
        name="dashboard",
    ),

    path(
        "dashboard/",
        views.lms_dashboard,
        name="lms_dashboard",
    ),


    # =========================================================
    # LEARNING RESOURCES
    # =========================================================

    path(
        "resources/",
        views.resources,
        name="resources",
    ),

    path(
        "resources/documents/",
        views.resource_documents,
        name="documents",
    ),

    path(
        "resources/videos/",
        views.resource_videos,
        name="videos",
    ),

    path(
        "resources/links/",
        views.resource_links,
        name="links",
    ),

    path(
        "resources/add/",
        views.resource_create,
        name="resource_create",
    ),

    path(
        "resources/delete/<int:pk>/",
        views.resource_delete,
        name="resource_delete",
    ),


    # =========================================================
    # DIGITAL LESSONS
    # =========================================================

    path(
        "lessons/",
        views.lessons,
        name="lessons",
    ),

    path(
        "lessons/create/",
        views.lesson_create,
        name="lesson_create",
    ),

    path(
        "lessons/my/",
        views.my_lessons,
        name="my_lessons",
    ),

    path(
        "lessons/learners/",
        views.learner_lessons,
        name="learner_lessons",
    ),

    path(
        "lessons/<int:pk>/",
        views.lesson_detail,
        name="lesson_detail",
    ),

    path(
        "lessons/<int:pk>/edit/",
        views.lesson_edit,
        name="lesson_edit",
    ),

    path(
        "lessons/<int:pk>/delete/",
        views.lesson_delete,
        name="lesson_delete",
    ),


    # =========================================================
    # ASSIGNMENTS
    # =========================================================

    path(
        "assignments/",
        views.assignments,
        name="assignments",
    ),

    path(
        "assignments/create/",
        views.assignment_create,
        name="assignment_create",
    ),

    path(
        "assignments/my/",
        views.my_assignments,
        name="my_assignments",
    ),

    path(
        "assignments/learners/",
        views.learner_assignments,
        name="learner_assignments",
    ),

    path(
        "assignments/<int:pk>/",
        views.assignment_detail,
        name="assignment_detail",
    ),

    path(
        "assignments/<int:pk>/edit/",
        views.assignment_edit,
        name="assignment_edit",
    ),

    path(
        "assignments/<int:pk>/delete/",
        views.assignment_delete,
        name="assignment_delete",
    ),

    path(
        "assignments/<int:pk>/submit/",
        views.assignment_submit,
        name="assignment_submit",
    ),

    path(
        "assignments/<int:pk>/submissions/",
        views.assignment_submissions,
        name="assignment_submissions",
    ),

    path(
        "assignments/submissions/<int:pk>/mark/",
        views.assignment_mark,
        name="assignment_mark",
    ),


    # =========================================================
    # COURSES
    # =========================================================

    path(
        "courses/",
        views.courses,
        name="courses",
    ),

    path(
        "courses/create/",
        views.course_create,
        name="course_create",
    ),

    path(
        "courses/list/",
        views.course_list,
        name="course_list",
    ),

    path(
        "courses/<int:pk>/",
        views.course_detail,
        name="course_detail",
    ),


    # =========================================================
    # SUBJECTS
    # =========================================================

    path(
        "subjects/",
        views.subject_list,
        name="subject_list",
    ),


    # =========================================================
    # COURSE CLASSES
    # =========================================================

    path(
        "classes/",
        views.course_class_list,
        name="course_class_list",
    ),

]