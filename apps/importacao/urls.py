from django.urls import path

from . import views

app_name = "importacao"

urlpatterns = [
    path("alunos/", views.importar, name="importar"),
    path("alunos/modelo.csv", views.modelo_csv, name="modelo"),
    path("alunos/historico/", views.historico, name="historico"),
    path("alunos/<int:pk>/previa/", views.previa, name="previa"),
    path("alunos/<int:pk>/resultado/", views.resultado, name="resultado"),
    path("alunos/<int:pk>/rejeitadas.csv", views.erros_csv, name="erros_csv"),
]