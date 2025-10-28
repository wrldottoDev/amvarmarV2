# core/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = "core"

urlpatterns = [
    # -------------------------
    # AUTH / LANDING
    # -------------------------
    path("", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("index/", views.index, name="index"),
    path(
        "password/change/",
        auth_views.PasswordChangeView.as_view(
            template_name="password_change_form.html",
            success_url="/password/change/done/",
        ),
        name="password_change",
    ),
    path(
        "password/change/done/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="password_change_done.html"
        ),
        name="password_change_done",
    ),

    # -------------------------
    # CLIENTE (warehouses solo lectura + B/L)
    # -------------------------
    path("mis-warehouses/", views.my_warehouses, name="my_warehouses"),
    path(
        "mis-warehouses/<str:wr_number>/",
        views.warehouse_detail,                 # <-- vista CLIENTE
        name="client_warehouse_detail",
    ),
    path("mis-despachos/", views.my_dispatches, name="my_dispatches"),
    path("mis-despachos/<int:pk>/", views.my_dispatch_detail, name="my_dispatch_detail"),

    # -------------------------
    # ADMIN (panel, clientes)
    # -------------------------
    path("admin-panel/", views.admin_panel, name="admin_panel"),
    path("panel/clients/", views.clients_list, name="clients_list"),
    path("panel/clients/quick-create/", views.quick_create_client, name="quick_create_client"),

    # -------------------------
    # ADMIN (Despachos / B/L) — antes de <wr_number>
    # -------------------------
    path("admin-panel/dispatches/", views.dispatch_list, name="dispatch_list"),
    path("admin-panel/dispatches/<int:pk>/", views.dispatch_detail, name="dispatch_detail"),
    path("admin-panel/dispatches/<int:pk>/upload-bol/", views.upload_bol, name="upload_bol"),
    path("admin-panel/dispatches/<int:pk>/send-bol/", views.send_bol_to_user, name="send_bol_to_user"),

    # -------------------------
    # ADMIN (Warehouses)
    # -------------------------
    path("admin-panel/create/", views.create_warehouse, name="create_warehouse"),
    path("admin-panel/<str:wr_number>/edit/", views.edit_warehouse, name="edit_warehouse"),
    path("admin-panel/<str:wr_number>/delete/", views.delete_warehouse, name="delete_warehouse"),

    # Piezas (por pk o wr_number)
    path("admin-panel/<str:wr_number>/pieces/add/", views.add_piece, name="add_piece"),
    path("admin-panel/pieces/<int:pk>/edit/", views.edit_piece, name="edit_piece"),
    path("admin-panel/pieces/<int:pk>/delete/", views.delete_piece, name="delete_piece"),

    # Detalle ADMIN — al final para no comerse /dispatches/
    path(
        "admin-panel/<str:wr_number>/",
        views.admin_warehouse_detail,           # <-- vista ADMIN correcta
        name="admin_warehouse_detail",
    ),

    path("admin-panel/<str:wr_number>/items/", views.edit_items_for_warehouse, name="edit_items_for_warehouse"),
]
