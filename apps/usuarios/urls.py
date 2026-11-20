from django.urls import path

from . import views

app_name = "usuarios"

urlpatterns = [
    path("", views.UsuarioListView.as_view(), name="lista"),
    path("novo/", views.UsuarioCreateView.as_view(), name="criar"),
    path("senha/", views.SenhaView.as_view(), name="senha"),
    path("<int:pk>/editar/", views.UsuarioUpdateView.as_view(), name="editar"),
]
