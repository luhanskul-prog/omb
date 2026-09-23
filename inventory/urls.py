from django.urls import path

from . import views


app_name = "inventory"


urlpatterns = [

    # =========================================================
    # INVENTORY DASHBOARD
    # =========================================================

    path(
        "",
        views.inventory_dashboard,
        name="dashboard",
    ),

]