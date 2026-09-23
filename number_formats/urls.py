
from django.urls import path
from . import views

app_name = "number_formats"

urlpatterns = [
    path("", views.number_format_settings, name="settings"),
]
