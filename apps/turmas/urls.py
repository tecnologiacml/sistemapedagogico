from django.urls import path

from . import views

app_name = "turmas"

urlpatterns = [
    path("", views.TurmaListView.as_view(), name="lista"),
    path("nova/", views.TurmaCreateView.as_view(), name="criar"),
    path("importar-matriculas/", views.ImportarMatriculasView.as_view(), name="importar_matriculas"),
    path("importar-matriculas/alunos-sem-turma.csv", views.ExportarSemTurmaView.as_view(), name="alunos_sem_turma"),
    path("aluno/<int:aluno_pk>/matricular/", views.MatricularView.as_view(), name="matricular"),
    path("<int:pk>/editar/", views.TurmaUpdateView.as_view(), name="editar"),
]
