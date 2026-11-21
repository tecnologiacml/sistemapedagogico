from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeView
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from .forms import SenhaForm, UsuarioCriarForm, UsuarioEditarForm
from .mixins import PerfilRequiredMixin
from .models import Usuario


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
        return super().form_valid(form)


class UsuarioUpdateView(_SoAdministrador, UpdateView):
    form_class = UsuarioEditarForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario_logado"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Usuário atualizado.")
        return super().form_valid(form)



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
        messages.success(self.request, "Senha alterada com sucesso.")
        return resposta
