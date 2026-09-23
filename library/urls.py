from django.urls import path

from . import views
from .admin_lookup import lookup_member


urlpatterns = [
    # =========================================================
    # DASHBOARD
    # =========================================================
    path("", views.library_dashboard, name="dashboard"),
    path("dashboard/", views.library_dashboard, name="library_dashboard"),

    # =========================================================
    # BOOKS
    # =========================================================
    path("books/", views.books, name="books"),
    path("books/", views.books, name="library_books"),

    path("books/add/", views.book_add, name="book_add"),
    path("books/add/", views.book_add, name="library_book_add"),

    path("books/<int:pk>/edit/", views.book_edit, name="book_edit"),
    path("books/<int:pk>/edit/", views.book_edit, name="library_book_edit"),

    path("books/<int:pk>/delete/", views.book_delete, name="book_delete"),
    path("books/<int:pk>/delete/", views.book_delete, name="library_book_delete"),

    path("books/print/", views.book_print_list, name="book_print_list"),
    path("books/print/", views.book_print_list, name="library_book_print_list"),

    path("books/all/", views.book_all_list, name="book_all_list"),
    path("books/all/", views.book_all_list, name="library_book_all_list"),

    # =========================================================
    # CATEGORIES
    # =========================================================
    path("categories/", views.categories, name="categories"),
    path("categories/", views.categories, name="library_categories"),

    path("categories/add/", views.category_add, name="category_add"),
    path("categories/add/", views.category_add, name="library_category_add"),

    path("categories/<int:pk>/edit/", views.category_edit, name="category_edit"),
    path("categories/<int:pk>/edit/", views.category_edit, name="library_category_edit"),

    path("categories/<int:pk>/delete/", views.category_delete, name="category_delete"),
    path("categories/<int:pk>/delete/", views.category_delete, name="library_category_delete"),

    # =========================================================
    # MEMBERS
    # =========================================================
    path("members/", views.members, name="members"),
    path("members/", views.members, name="library_members"),

    path("members/add/", views.member_add, name="member_add"),
    path("members/add/", views.member_add, name="library_member_add"),

    path("members/<int:pk>/edit/", views.member_edit, name="member_edit"),
    path("members/<int:pk>/edit/", views.member_edit, name="library_member_edit"),

    path("members/<int:pk>/delete/", views.member_delete, name="member_delete"),
    path("members/<int:pk>/delete/", views.member_delete, name="library_member_delete"),

    path("members/print/", views.member_print, name="member_print"),
    path("members/print/", views.member_print, name="library_member_print"),

    path("members/staff/", views.staff_members, name="staff_members"),
    path("members/staff/", views.staff_members, name="library_staff_members"),

    path(
        "members/staff/print/",
        views.staff_members_print,
        name="staff_members_print",
    ),
    path(
        "members/staff/print/",
        views.staff_members_print,
        name="library_staff_members_print",
    ),

    path("members/students/", views.student_members, name="student_members"),
    path("members/students/", views.student_members, name="library_student_members"),

    path(
        "members/students/print/",
        views.student_members_print,
        name="student_members_print",
    ),
    path(
        "members/students/print/",
        views.student_members_print,
        name="library_student_members_print",
    ),

    # =========================================================
    # ISSUES
    # =========================================================
    path("issues/", views.issues, name="issues"),
    path("issues/", views.issues, name="library_issues"),

    path("issues/add/", views.issue_add, name="issue_add"),
    path("issues/add/", views.issue_add, name="library_issue_add"),

    path("issues/<int:pk>/edit/", views.issue_edit, name="issue_edit"),
    path("issues/<int:pk>/edit/", views.issue_edit, name="library_issue_edit"),

    path("issues/<int:pk>/return/", views.issue_return, name="issue_return"),
    path("issues/<int:pk>/return/", views.issue_return, name="library_issue_return"),

    # =========================================================
    # RETURNS
    # =========================================================
    path("returns/", views.returns, name="returns"),
    path("returns/", views.returns, name="library_returns"),

    # =========================================================
    # REPORTS
    # =========================================================
    path("reports/", views.reports, name="reports"),
    path("reports/", views.reports, name="library_reports"),

    # =========================================================
    # MEMBER LOOKUP
    # =========================================================
    path(
        "admin/member-lookup/",
        lookup_member,
        name="member_lookup",
    ),
]

