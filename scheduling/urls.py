from django.urls import path

from . import views
from . import timetable_centre
app_name = "scheduling"


urlpatterns = [
    path(
        "management-centre/configuration/<int:configuration_id>/",
        timetable_centre.timetable_slot_configuration,
        name="timetable_slot_configuration",
    ),
    path(
        "management-centre/configuration/<int:configuration_id>/slots/add/",
        timetable_centre.timetable_slot_add,
        name="timetable_slot_add",
    ),
    path(
        "management-centre/slots/<int:slot_id>/delete/",
        timetable_centre.timetable_slot_delete,
        name="timetable_slot_delete",
    ),
    path(
        "management-centre/configuration/<int:configuration_id>/assign-lessons/",
        timetable_centre.timetable_assign_lessons,
        name="timetable_assign_lessons",
    ),
    path(
        "management-centre/configuration/<int:configuration_id>/assign-lessons/add/",
        timetable_centre.timetable_assignment_add,
        name="timetable_centre_assignment_add",
    ),
    path(
        "management-centre/configuration/<int:configuration_id>/assignments/<int:assignment_id>/delete/",
        timetable_centre.timetable_assignment_delete,
        name="timetable_centre_assignment_delete",
    ),
    path(
        "management-centre/teachers/",
        timetable_centre.timetable_teachers,
        name="timetable_teachers",
    ),
    path(
        "management-centre/classes/",
        timetable_centre.timetable_classes,
        name="timetable_classes",
    ),
    path(
        "management-centre/streams/",
        timetable_centre.timetable_streams,
        name="timetable_streams",
    ),
    path(
        "management-centre/subjects/",
        timetable_centre.timetable_subjects,
        name="timetable_subjects",
    ),
    path("management-centre/", timetable_centre.timetable_management_centre, name="timetable_management_centre"),
    path("management-centre/create/", timetable_centre.timetable_create_select, name="timetable_create_select"),
    path("review/", views.timetable_review, name="timetable_review"),

    path(
        "publish/",
        views.publish_timetable,
        name="publish_timetable",
    ),

    path(
        "unpublish/",
        views.unpublish_timetable,
        name="unpublish_timetable",
    ),

    path(
        "published/",
        views.published_timetable_view,
        name="published_timetable",
    ),

    path("generate/", views.timetable_generator, name="timetable_generator"),

    # =========================================================
    # DASHBOARD
    # =========================================================

    path(
        "",
        views.scheduling_dashboard,
        name="scheduling_dashboard",
    ),


    # =========================================================
    # TIMETABLE
    # =========================================================

    path(
        "timetable/",
        views.timetable_view,
        name="timetable",
    ),

    path(
        "timetable/add/",
        views.add_timetable_entry,
        name="add_timetable_entry",
    ),

    path(
        "timetable/<int:entry_id>/edit/",
        views.edit_timetable_entry,
        name="edit_timetable_entry",
    ),

    path(
        "timetable/<int:entry_id>/delete/",
        views.delete_timetable_entry,
        name="delete_timetable_entry",
    ),


    # =========================================================
    # SUBJECTS
    # =========================================================

    path(
        "subjects/",
        views.subject_list,
        name="subject_list",
    ),

    path(
        "subjects/add/",
        views.subject_add,
        name="subject_add",
    ),

    path(
        "subjects/<int:subject_id>/edit/",
        views.subject_edit,
        name="subject_edit",
    ),

    path(
        "subjects/<int:subject_id>/delete/",
        views.subject_delete,
        name="subject_delete",
    ),


    # =========================================================
    # TEACHERS
    # =========================================================

    path(
        "teachers/",
        views.teacher_list,
        name="teacher_list",
    ),

    path(
        "teachers/add/",
        views.teacher_add,
        name="teacher_add",
    ),

    path(
        "teachers/<int:teacher_id>/edit/",
        views.teacher_edit,
        name="teacher_edit",
    ),

    path(
        "teachers/<int:teacher_id>/delete/",
        views.teacher_delete,
        name="teacher_delete",
    ),


    # =========================================================
    # TEACHER TEACHING ASSIGNMENTS
    # =========================================================

    path(
        "teaching-assignments/",
        views.teacher_teaching_assignment_list,
        name="teacher_teaching_assignment_list",
    ),

    path(
        "teaching-assignments/add/",
        views.teacher_teaching_assignment_add,
        name="teacher_teaching_assignment_add",
    ),

    path(
        "teaching-assignments/<int:assignment_id>/edit/",
        views.teacher_teaching_assignment_edit,
        name="teacher_teaching_assignment_edit",
    ),

    path(
        "teaching-assignments/<int:assignment_id>/delete/",
        views.teacher_teaching_assignment_delete,
        name="teacher_teaching_assignment_delete",
    ),


    # =========================================================
    # ROOMS
    # =========================================================

    path(
        "rooms/",
        views.room_list,
        name="room_list",
    ),

    path(
        "rooms/add/",
        views.room_add,
        name="room_add",
    ),

    path(
        "rooms/<int:room_id>/edit/",
        views.room_edit,
        name="room_edit",
    ),

    path(
        "rooms/<int:room_id>/delete/",
        views.room_delete,
        name="room_delete",
    ),


    # =========================================================
    # PERIODS
    # =========================================================

    path(
        "periods/",
        views.period_list,
        name="period_list",
    ),

    path(
        "periods/add/",
        views.period_add,
        name="period_add",
    ),

    path(
        "periods/<int:period_id>/edit/",
        views.period_edit,
        name="period_edit",
    ),

    path(
        "periods/<int:period_id>/delete/",
        views.period_delete,
        name="period_delete",
    ),


    # =========================================================
    # DAYS
    # =========================================================

    path(
        "days/",
        views.day_list,
        name="day_list",
    ),

    path(
        "days/add/",
        views.day_add,
        name="day_add",
    ),

    path(
        "days/<int:day_id>/edit/",
        views.day_edit,
        name="day_edit",
    ),

    path(
        "days/<int:day_id>/delete/",
        views.day_delete,
        name="day_delete",
    ),


    # =========================================================
    # EXAMS
    # =========================================================

    path(
        "exams/",
        views.exam_list,
        name="exam_list",
    ),

    path(
        "exams/add/",
        views.exam_add,
        name="exam_add",
    ),

    path(
        "exams/<int:exam_id>/edit/",
        views.exam_edit,
        name="exam_edit",
    ),

    path(
        "exams/<int:exam_id>/delete/",
        views.exam_delete,
        name="exam_delete",
    ),


    # =========================================================
    # TEACHER SUBSTITUTIONS
    # =========================================================

    path(
        "substitutions/",
        views.substitution_list,
        name="substitution_list",
    ),

    path(
        "substitutions/add/",
        views.substitution_add,
        name="substitution_add",
    ),

    path(
        "substitutions/<int:substitution_id>/edit/",
        views.substitution_edit,
        name="substitution_edit",
    ),

    path(
        "substitutions/<int:substitution_id>/delete/",
        views.substitution_delete,
        name="substitution_delete",
    ),


    path(
        "complete/",
        views.complete_timetable_centre,
        name="complete_timetable_centre",
    ),

    path(
        "assign/",
        views.timetable_assignment_add,
        name="timetable_assignment_add",
    ),

    path(
        "assign/<int:pk>/delete/",
        views.timetable_assignment_delete,
        name="timetable_assignment_delete",
    ),

    path(
        "slot-rule/",
        views.timetable_slot_rule_save,
        name="timetable_slot_rule_save",
    ),

    path(
        "check-complete/",
        views.timetable_check_view,
        name="timetable_check_complete",
    ),

    path(
        "print/class/",
        views.timetable_print_class,
        name="timetable_print_class",
    ),

    path(
        "print/teacher/",
        views.timetable_print_teacher,
        name="timetable_print_teacher",
    ),

    path(
        "print/school/",
        views.timetable_print_school,
        name="timetable_print_school",
    ),

    path(
        "teacher/",
        views.teacher_published_timetable,
        name="teacher_published_timetable",
    ),
]


