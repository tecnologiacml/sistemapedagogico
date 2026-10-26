from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class PerfilRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Exige login e uma permissão do usuário (verificada no servidor).

    Defina `permissao` com o nome de uma propriedade booleana de Usuario.
    Sem login -> redireciona ao login. Logado sem permissão -> 403.
    """

    permissao = None

    def test_func(self):
        if self.permissao is None:
            return True
        return getattr(self.request.user, self.permissao, False)
