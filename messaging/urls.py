from django.urls import path

from . import views


app_name = "messaging"


urlpatterns = [

    # =========================================================
    # PORTAL MESSAGES
    # =========================================================

    path(
        "portal/",
        views.portal_messages,
        name="portal_messages",
    ),

    path(
        "portal/sent/",
        views.portal_sent_messages,
        name="portal_sent_messages",
    ),


    # =========================================================
    # MESSAGING DASHBOARD
    # =========================================================

    path(
        "",
        views.messaging_dashboard,
        name="dashboard",
    ),


    # =========================================================
    # COMPOSE MESSAGE
    # =========================================================

    path(
        "compose/",
        views.message_compose,
        name="compose",
    ),

    path(
        "compose/recipient-lookup/",
        views.compose_recipient_lookup,
        name="compose_recipient_lookup",
    ),


    # =========================================================
    # ADMIN MESSAGE APPROVALS
    # =========================================================

    path(
        "approvals/",
        views.pending_approvals,
        name="pending_approvals",
    ),

    path(
        "approvals/<int:message_id>/approve/",
        views.approve_message,
        name="approve_message",
    ),

    path(
        "approvals/<int:message_id>/reject/",
        views.reject_message,
        name="reject_message",
    ),


    # =========================================================
    # RECEIVED MESSAGE
    # =========================================================

    path(
        "message/<int:message_id>/",
        views.message_detail,
        name="message_detail",
    ),


    # =========================================================
    # REPLY TO MESSAGE
    # =========================================================

    path(
        "message/<int:message_id>/reply/",
        views.message_reply,
        name="message_reply",
    ),


    # =========================================================
    # SENT MESSAGE
    # =========================================================

    path(
        "sent/<int:message_id>/",
        views.sent_message_detail,
        name="sent_message_detail",
    ),

]