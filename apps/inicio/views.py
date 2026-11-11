from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class InicioView(LoginRequiredMixin, TemplateView):
    """Tela de entrada: só a identidade do sistema. Os painéis ficam no menu lateral, quando existirem."""

    template_name = "inicio/inicio.html"
