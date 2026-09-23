
from django.urls import path
from . import views

app_name = "professional_documents"

urlpatterns = [

    path(
        "",
        views.portal,
        name="portal",
    ),

    path(
        "staff/",
        views.staff_documents,
        name="staff_documents",
    ),

    path(
        "admin/",
        views.admin_documents,
        name="admin_documents",
    ),

    path(
        "create/",
        views.document_create,
        name="create",
    ),

    path(
        "<int:pk>/",
        views.document_detail,
        name="detail",
    ),

    path(
        "<int:pk>/edit/",
        views.document_edit,
        name="edit",
    ),

    path(
        "<int:pk>/submit/",
        views.document_submit,
        name="submit",
    ),

    path(
        "<int:pk>/review/",
        views.document_review,
        name="review",
    ),
]
