from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from apps.alunos.models import Aluno


class InicioView(LoginRequiredMixin, TemplateView):
    """Painel inicial (dashboard). Turmas e desempenho entram quando esses módulos existirem."""

    template_name = "inicio/inicio.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["total_alunos"] = Aluno.objects.count()
        return ctx
