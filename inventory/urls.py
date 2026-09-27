from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("items/", views.item_list, name="item_list"),
    path("items/add/", views.item_create, name="item_create"),
    path("items/import/", views.import_items_csv, name="import_items_csv"),
    path("items/import/template/", views.download_items_csv_template, name="download_items_csv_template"),
    path("items/<int:pk>/", views.item_detail, name="item_detail"),
    path("items/<int:pk>/edit/", views.item_edit, name="item_edit"),
    path("categories/", views.category_list, name="category_list"),
    path("categories/add/", views.category_create, name="category_create"),
    path("suppliers/", views.supplier_list, name="supplier_list"),
    path("suppliers/add/", views.supplier_create, name="supplier_create"),
    path("stock/", views.stock_list, name="stock_list"),
    path("stock/add/", views.stock_create, name="stock_create"),
    path("purchases/", views.purchase_list, name="purchase_list"),
    path("purchases/add/", views.purchase_create, name="purchase_create"),
    path("purchases/<int:pk>/", views.purchase_detail, name="purchase_detail"),
    path("purchases/<int:pk>/receive/", views.purchase_receive, name="purchase_receive"),
    path("assets/", views.asset_list, name="asset_list"),
    path("assets/add/", views.asset_create, name="asset_create"),
    path("assets/<int:pk>/edit/", views.asset_edit, name="asset_edit"),
    path("reports/", views.inventory_report, name="inventory_report"),
    path("export/items/", views.export_items_csv, name="export_items_csv"),
]
