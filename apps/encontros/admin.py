from django.contrib import admin

from .models import Encontro


@admin.register(Encontro)
class EncontroAdmin(admin.ModelAdmin):
    list_display = ("aluno", "numero", "data", "presente", "encaminhamento")
    list_filter = ("presente", "encaminhamento")
    search_fields = ("aluno__nome", "aluno__ra")
