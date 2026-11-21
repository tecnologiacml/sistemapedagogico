from datetime import timedelta

from django.conf import settings
from django.contrib.sessions.models import Session
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Usuario

PROTEGIDAS = ("home", "alunos:lista", "encontros:lista")


class EncerramentoDeSessaoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = Usuario.objects.create_user(
            "orient", email="o@t.local", password="Teste@12345", perfil=Usuario.Perfil.ORIENTADOR
        )

    def entrar(self):
        self.client.force_login(self.usuario)

    def test_sair_exige_post(self):
        self.entrar()
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        # continua logado: um link/imagem não consegue deslogar a pessoa
        self.assertEqual(self.client.get(reverse("alunos:lista")).status_code, 200)

    def test_depois_de_sair_links_protegidos_vao_para_o_login(self):
        self.entrar()
        r = self.client.post(reverse("logout"))
        self.assertRedirects(r, reverse("login"), fetch_redirect_response=False)
        for nome in PROTEGIDAS:
            url = reverse(nome)
            self.assertRedirects(
                self.client.get(url), f"{reverse('login')}?next={url}", fetch_redirect_response=False
            )

    def test_cookie_da_sessao_antiga_deixa_de_valer(self):
        self.entrar()
        id_antigo = self.client.cookies["sessionid"].value
        self.client.post(reverse("logout"))
        outro = Client()
        outro.cookies["sessionid"] = id_antigo
        url = reverse("alunos:lista")
        self.assertRedirects(outro.get(url), f"{reverse('login')}?next={url}", fetch_redirect_response=False)

    def test_paginas_de_quem_esta_logado_nao_vao_para_o_cache(self):
        self.entrar()
        for nome in PROTEGIDAS:
            cache = self.client.get(reverse(nome))["Cache-Control"]
            self.assertIn("no-store", cache)
            self.assertIn("no-cache", cache)


class ExpiracaoPorInatividadeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = Usuario.objects.create_user(
            "orient", email="o@t.local", password="Teste@12345", perfil=Usuario.Perfil.ORIENTADOR
        )

    def test_configuracao_de_15_minutos(self):
        self.assertEqual(settings.SESSION_COOKIE_AGE, 15 * 60)
        self.assertTrue(settings.SESSION_SAVE_EVERY_REQUEST)  # cada página aberta renova o prazo
        self.assertTrue(settings.SESSION_EXPIRE_AT_BROWSER_CLOSE)

    def test_sessao_ganha_prazo_de_15_minutos(self):
        self.client.force_login(self.usuario)
        self.client.get(reverse("alunos:lista"))
        sessao = Session.objects.get()
        restante = sessao.expire_date - timezone.now()
        self.assertLessEqual(restante, timedelta(minutes=15))
        self.assertGreater(restante, timedelta(minutes=14))

    def test_sessao_vencida_pede_login_de_novo(self):
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.get(reverse("alunos:lista")).status_code, 200)
        Session.objects.update(expire_date=timezone.now() - timedelta(seconds=1))
        url = reverse("alunos:lista")
        self.assertRedirects(
            self.client.get(url), f"{reverse('login')}?next={url}", fetch_redirect_response=False
        )