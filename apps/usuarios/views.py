from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeView
from django.db import transaction
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from .auditoria import dados_iniciais, diferencas, registrar, snapshot
from .forms import SenhaForm, UsuarioCriarForm, UsuarioEditarForm
from .mixins import PerfilRequiredMixin
from .models import RegistroAuditoria, Usuario


class _SoAdministrador(PerfilRequiredMixin):
    permissao = "pode_gerenciar_usuarios"
    model = Usuario
    success_url = reverse_lazy("usuarios:lista")


class UsuarioListView(_SoAdministrador, ListView):
    paginate_by = 20

    def get_queryset(self):
        qs = Usuario.objects.order_by("first_name", "username")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(first_name__icontains=q) | Q(last_name__icontains=q)
                | Q(username__icontains=q) | Q(email__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "").strip()
        return ctx


class UsuarioCreateView(_SoAdministrador, CreateView):
    form_class = UsuarioCriarForm

    def form_valid(self, form):
        messages.success(
            self.request,
            "Usuário cadastrado. Passe o usuário e a senha para a pessoa por um canal seguro.",
        )
        with transaction.atomic():
            resposta = super().form_valid(form)
            registrar(
                self.object, self.request.user, RegistroAuditoria.Acao.CRIADO,
                dados_iniciais(snapshot(self.object)),
            )
        return resposta


class UsuarioUpdateView(_SoAdministrador, UpdateView):
    form_class = UsuarioEditarForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario_logado"] = self.request.user
        return kwargs

    def get_object(self, queryset=None):
        usuario = super().get_object(queryset)
        # foto de antes de o formulário mexer na instância
        self._antes = snapshot(usuario)
        return usuario

    def form_valid(self, form):
        messages.success(self.request, "Usuário atualizado.")
        with transaction.atomic():
            resposta = super().form_valid(form)
            mudancas = diferencas(self._antes, snapshot(self.object))
            if mudancas:
                registrar(self.object, self.request.user, RegistroAuditoria.Acao.ALTERADO, mudancas)
            if form.cleaned_data.get("nova_senha"):
                registrar(self.object, self.request.user, RegistroAuditoria.Acao.SENHA_REDEFINIDA)
        return resposta


class AuditoriaListView(_SoAdministrador, ListView):
    """Histórico de alterações das contas. Só o administrador consulta."""

    model = RegistroAuditoria
    template_name = "usuarios/auditoria_list.html"
    paginate_by = 30

    def get_queryset(self):
        qs = RegistroAuditoria.objects.select_related("alvo", "feito_por")
        usuario = self.request.GET.get("usuario", "")
        if usuario.isdigit():
            qs = qs.filter(alvo_id=int(usuario))
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(alvo_username__icontains=q) | Q(feito_por_username__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "").strip()
        usuario = self.request.GET.get("usuario", "")
        ctx["usuario_sel"] = usuario if usuario.isdigit() else ""
        return ctx


class SenhaView(LoginRequiredMixin, PasswordChangeView):
    """Qualquer pessoa logada troca a própria senha. Quem entrou com senha provisória é levado até aqui."""

    template_name = "usuarios/senha.html"
    form_class = SenhaForm
    success_url = reverse_lazy("home")

    def form_valid(self, form):
        resposta = super().form_valid(form)
        usuario = self.request.user
        if usuario.precisa_trocar_senha:
            usuario.precisa_trocar_senha = False
            usuario.save(update_fields=["precisa_trocar_senha"])
        registrar(usuario, usuario, RegistroAuditoria.Acao.SENHA_ALTERADA)
        messages.success(self.request, "Senha alterada com sucesso.")
        return resposta
