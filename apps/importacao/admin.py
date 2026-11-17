from django.contrib import admin

from .models import Importacao, ImportacaoLinha


class LinhaInline(admin.TabularInline):
    model = ImportacaoLinha
    extra = 0
    can_delete = False
    fields = ("numero_linha", "nome", "ra", "situacao", "motivo", "aviso")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Importacao)
class ImportacaoAdmin(admin.ModelAdmin):
    list_display = ("arquivo_nome", "usuario", "status", "total_linhas", "qtd_criados", "qtd_atualizados", "qtd_rejeitados", "criado_em")
    list_filter = ("status", "unidade")
    inlines = [LinhaInline]