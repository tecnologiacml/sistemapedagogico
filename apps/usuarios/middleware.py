from django.shortcuts import redirect
from django.urls import reverse


class TrocaSenhaObrigatoriaMiddleware:
    """Quem entrou com a senha provisória só consegue abrir a tela de trocar a senha (ou sair)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        usuario = request.user
        if usuario.is_authenticated and getattr(usuario, "precisa_trocar_senha", False):
            liberados = (reverse("usuarios:senha"), reverse("logout"))
            if request.path not in liberados and not request.path.startswith("/static/"):
                return redirect("usuarios:senha")
        return self.get_response(request)
