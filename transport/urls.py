from django.urls import path
from . import views


app_name = "transport"


urlpatterns = [

    # =========================================================
    # TRANSPORT DASHBOARD
    # =========================================================

    path(
        "",
        views.transport_dashboard,
        name="dashboard",
    ),

]