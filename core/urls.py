from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('index/', views.index, name='index'),
    

    # Panel de administración
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('admin-panel/create/', views.create_warehouse, name='create_warehouse'),
    path('admin-panel/<str:wr_number>/', views.warehouse_detail, name='warehouse_detail'),
    path('admin-panel/<str:wr_number>/delete/', views.delete_warehouse, name='delete_warehouse'),
    path('admin-panel/<str:wr_number>/edit/', views.edit_warehouse, name='edit_warehouse'),

    # piezas
    path('admin-panel/<str:wr_number>/pieces/add/', views.add_piece, name='add_piece'),
    path('admin-panel/pieces/<int:pk>/edit/', views.edit_piece, name='edit_piece'),
    path('admin-panel/pieces/<int:pk>/delete/', views.delete_piece, name='delete_piece'),

    # Clientes (usuarios no staff)
    path("panel/clients/", views.clients_list, name="clients_list"),
    path("panel/clients/quick-create/", views.quick_create_client, name="quick_create_client"),
]