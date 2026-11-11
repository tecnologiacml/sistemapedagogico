from django.contrib import admin

from .models import Aluno, Responsavel


@admin.register(Responsavel)
class ResponsavelAdmin(admin.ModelAdmin):
    list_display = ("nome", "email", "celular")
    search_fields = ("nome", "email")


@admin.register(Aluno)
class AlunoAdmin(admin.ModelAdmin):
    list_display = ("nome", "matricula", "ra", "unidade", "responsavel")
    list_filter = ("unidade",)
    search_fields = ("nome", "matricula", "ra")
    autocomplete_fields = ("responsavel",)