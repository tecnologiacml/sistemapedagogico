from django.contrib import admin

from .models import Aluno, Responsavel


@admin.register(Responsavel)
class ResponsavelAdmin(admin.ModelAdmin):
    list_display = ("nome", "email", "celular")
    search_fields = ("nome", "email")


@admin.register(Aluno)
class AlunoAdmin(admin.ModelAdmin):
    list_display = ("ra", "nome", "serie", "cpf", "matricula", "unidade", "responsavel")

    list_filter = ("unidade",)

    search_fields = ("nome", "cpf", "ra", "matricula")

    autocomplete_fields = ("responsavel",)