from django.utils.cache import add_never_cache_headers


class NaoGuardarEmCacheMiddleware:
    """Páginas de quem está logado não ficam no cache do navegador.

    Sem isso, depois de sair, o botão "Voltar" mostraria a última página aberta
    (com dados de alunos) guardada em cache. Com "no-store", o navegador pede de novo
    ao servidor, que manda a pessoa para o login.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        resposta = self.get_response(request)
        if request.user.is_authenticated:
            add_never_cache_headers(resposta)
        return resposta
