from django.urls import path

from . import views

app_name = "alunos"

urlpatterns = [
    path("", views.AlunoListView.as_view(), name="lista"),
    path("novo/", views.AlunoCreateView.as_view(), name="criar"),
    path("<int:pk>/", views.AlunoDetailView.as_view(), name="detalhe"),
    path("<int:pk>/editar/", views.AlunoUpdateView.as_view(), name="editar"),
    path("<int:pk>/excluir/", views.AlunoDeleteView.as_view(), name="excluir"),
]
