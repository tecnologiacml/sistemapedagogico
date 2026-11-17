from django.contrib import admin

from .models import Aluno


@admin.register(Aluno)
class AlunoAdmin(admin.ModelAdmin):
    list_display = ("ra", "nome", "serie", "cpf")
    search_fields = ("nome", "cpf", "ra")
