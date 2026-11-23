from django.urls import path

from . import views

app_name = "turmas"

urlpatterns = [
    path("", views.TurmaListView.as_view(), name="lista"),
    path("nova/", views.TurmaCreateView.as_view(), name="criar"),
    path("<int:pk>/editar/", views.TurmaUpdateView.as_view(), name="editar"),
]
