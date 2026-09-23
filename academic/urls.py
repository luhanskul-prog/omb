from django.urls import path
from . import views
from . import assessment_countdown
from . import excel_marks
from . import excel_marks_upload
from . import excel_subject_marks


app_name = "academic"


urlpatterns = [
    path("marks/excel/upload/", excel_marks_upload.upload_marks_excel, name="excel_upload"),

    path(
        "assessment-countdown/",
        assessment_countdown.assessment_countdown,
        name="assessment_countdown",
    ),

    path(
        "marks/excel/individual/",
        excel_marks.individual_excel_marks,
        name="excel_individual",
    ),
    path(
        "marks/excel/class/",
        excel_marks.class_excel_marks,
        name="excel_class",
    ),


    path(
        "assessments/",
        views.assessment_management,
        name="assessment_management"
    ),

    path(
        "assessments/marks-template/",
        views.assessment_marks_template,
        name="assessment_marks_template"
    ),


    path(
        "",
        views.academic_dashboard,
        name="dashboard"
    ),

    path(
        "marks/",
        views.marks_entry,
        name="marks_entry"
    ),

    path(
        "class-list/",
        views.class_list,
        name="class_list"
    ),

    path(
        "report-cards/",
        views.report_cards,
        name="report_cards"
    ),

    path(
        "report-card/<int:student_id>/<int:academic_year_id>/<int:term_id>/",
        views.student_report_card,
        name="report_card"
    ),

    path(
        "results/",
        views.academic_results,
        name="academic_results"
    ),

    path(
        "performance/",
        views.performance_analysis,
        name="performance_analysis"
    ),

        path(
        "marks/excel/individual/upload/",
        excel_marks_upload.upload_individual_marks_excel,
        name="excel_upload_individual",
    ),
    path(
        "marks/excel/class/upload/",
        excel_marks_upload.upload_class_marks_excel,
        name="excel_upload_class",
    ),
path(
        "marks/excel/subject/generate/",
        excel_subject_marks.generate_subject_marks,
        name="excel_generate_subject",
    ),
    path(
        "marks/excel/subject/upload/",
        excel_subject_marks.upload_subject_marks,
        name="excel_upload_subject",
    ),
]