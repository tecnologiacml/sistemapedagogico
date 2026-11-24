from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .auditoria import dados_iniciais, diferencas, registrar, snapshot
from .models import RegistroAuditoria, Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ("username", "first_name", "last_name", "email", "perfil", "is_active")
    list_filter = ("perfil", "is_active")
    fieldsets = UserAdmin.fieldsets + (("Perfil de acesso", {"fields": ("perfil",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Perfil de acesso", {"fields": ("perfil",)}),
    )

    def has_delete_permission(self, request, obj=None):
        # Usuários não são apagados, para manter o histórico (desative a conta).
        return False

    def save_model(self, request, obj, form, change):
        antes = snapshot(Usuario.objects.get(pk=obj.pk)) if change else None
        super().save_model(request, obj, form, change)
        depois = snapshot(obj)
        if not change:
            registrar(obj, request.user, RegistroAuditoria.Acao.CRIADO, dados_iniciais(depois))
        else:
            mudancas = diferencas(antes, depois)
            if mudancas:
                registrar(obj, request.user, RegistroAuditoria.Acao.ALTERADO, mudancas)

    def user_change_password(self, request, id, form_url=""):
        resposta = super().user_change_password(request, id, form_url)
        if request.method == "POST" and resposta.status_code == 302:
            alvo = Usuario.objects.filter(pk=id).first()
            if alvo:
                registrar(alvo, request.user, RegistroAuditoria.Acao.SENHA_REDEFINIDA)
        return resposta


@admin.register(RegistroAuditoria)
class RegistroAuditoriaAdmin(admin.ModelAdmin):
    """Somente leitura: o registro de auditoria não se edita nem se apaga."""

    list_display = ("em", "acao", "alvo_username", "feito_por_username")
    list_filter = ("acao",)
    search_fields = ("alvo_username", "feito_por_username")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
