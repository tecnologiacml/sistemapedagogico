from django.urls import path

from . import views

app_name = "encontros"

urlpatterns = [
    path("", views.EncontroListView.as_view(), name="lista"),
    path("novo/", views.EncontroCreateView.as_view(), name="criar"),
    path("buscar-aluno/", views.BuscarAlunoView.as_view(), name="buscar_aluno"),
    path("aluno/<int:pk>/", views.AlunoEncontrosView.as_view(), name="aluno"),
    path("<int:pk>/", views.EncontroDetailView.as_view(), name="detalhe"),
]