from django.contrib import admin

from .models import AnoLetivo, Matricula, Serie, Turma, Unidade


@admin.register(Unidade)
class UnidadeAdmin(admin.ModelAdmin):
    list_display = ("nome", "ativa")


@admin.register(AnoLetivo)
class AnoLetivoAdmin(admin.ModelAdmin):
    list_display = ("ano", "inicio", "fim")


@admin.register(Serie)
class SerieAdmin(admin.ModelAdmin):
    list_display = ("nome", "ordem")


@admin.register(Turma)
class TurmaAdmin(admin.ModelAdmin):
    list_display = ("nome", "serie", "unidade", "ano_letivo", "ativa")
    list_filter = ("ano_letivo", "unidade", "ativa")
    search_fields = ("nome", "serie__nome")


@admin.register(Matricula)
class MatriculaAdmin(admin.ModelAdmin):
    list_display = ("aluno", "turma", "situacao", "data_inicio", "data_fim")
    list_filter = ("situacao", "turma__ano_letivo", "turma__unidade")
    search_fields = ("aluno__nome", "aluno__ra")
    raw_id_fields = ("aluno",)
