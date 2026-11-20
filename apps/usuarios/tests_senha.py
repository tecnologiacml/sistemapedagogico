from django.test import TestCase
from django.urls import reverse

from .models import Usuario

P = Usuario.Perfil
SENHA_PROVISORIA = "Provisoria#2026x"
SENHA_NOVA = "MinhaSenhaNova#2026"


class SenhaProvisoriaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = Usuario.objects.create_user("adm", email="adm@t.local", password="x", perfil=P.ADMINISTRADOR)
        cls.comum = Usuario.objects.create_user("ori", email="ori@t.local", password="x", perfil=P.ORIENTADOR)

    def cadastrar(self, **extra):
        self.client.force_login(self.admin)
        dados = {
            "first_name": "Nova", "last_name": "Pessoa", "username": "nova", "email": "nova@t.local",
            "perfil": "orientador", "password1": SENHA_PROVISORIA, "password2": SENHA_PROVISORIA,
        }
        dados.update(extra)
        return self.client.post(reverse("usuarios:criar"), dados)

    def test_admin_cadastra_com_senha_provisoria(self):
        r = self.cadastrar()
        self.assertEqual(r.status_code, 302)
        nova = Usuario.objects.get(username="nova")
        self.assertTrue(nova.precisa_trocar_senha)
        self.assertTrue(nova.check_password(SENHA_PROVISORIA))

    def test_quem_tem_senha_provisoria_so_acessa_a_troca_de_senha(self):
        self.cadastrar()
        self.client.logout()
        self.assertTrue(self.client.login(username="nova", password=SENHA_PROVISORIA))
        for nome in ("home", "alunos:lista", "encontros:lista"):
            self.assertRedirects(self.client.get(reverse(nome)), reverse("usuarios:senha"))
        r = self.client.get(reverse("usuarios:senha"))
        self.assertContains(r, "senha provisória")
        # sair continua funcionando
        self.assertEqual(self.client.post(reverse("logout")).status_code, 302)

    def test_trocar_a_senha_libera_o_sistema(self):
        self.cadastrar()
        self.client.logout()
        self.client.login(username="nova", password=SENHA_PROVISORIA)
        r = self.client.post(reverse("usuarios:senha"), {
            "old_password": SENHA_PROVISORIA, "new_password1": SENHA_NOVA, "new_password2": SENHA_NOVA,
        })
        self.assertRedirects(r, reverse("home"))
        nova = Usuario.objects.get(username="nova")
        self.assertFalse(nova.precisa_trocar_senha)
        self.assertTrue(nova.check_password(SENHA_NOVA))
        self.assertFalse(nova.check_password(SENHA_PROVISORIA))
        self.assertEqual(self.client.get(reverse("home")).status_code, 200)  # continua logada

    def test_senha_atual_errada_nao_troca(self):
        self.cadastrar()
        self.client.logout()
        self.client.login(username="nova", password=SENHA_PROVISORIA)
        r = self.client.post(reverse("usuarios:senha"), {
            "old_password": "errada", "new_password1": SENHA_NOVA, "new_password2": SENHA_NOVA,
        })
        self.assertEqual(r.status_code, 200)
        self.assertTrue(Usuario.objects.get(username="nova").precisa_trocar_senha)

    def test_nova_senha_igual_a_atual_e_recusada(self):
        self.cadastrar()
        self.client.logout()
        self.client.login(username="nova", password=SENHA_PROVISORIA)
        r = self.client.post(reverse("usuarios:senha"), {
            "old_password": SENHA_PROVISORIA, "new_password1": SENHA_PROVISORIA, "new_password2": SENHA_PROVISORIA,
        })
        self.assertContains(r, "precisa ser diferente")

    def test_senhas_novas_diferentes_entre_si_sao_recusadas(self):
        self.client.force_login(self.comum)
        r = self.client.post(reverse("usuarios:senha"), {
            "old_password": "x", "new_password1": SENHA_NOVA, "new_password2": SENHA_NOVA + "9",
        })
        self.assertEqual(r.status_code, 200)

    def test_usuario_antigo_nao_e_forcado(self):
        self.client.force_login(self.comum)
        self.assertEqual(self.client.get(reverse("home")).status_code, 200)

    def test_pagina_exige_login(self):
        r = self.client.get(reverse("usuarios:senha"))
        self.assertRedirects(r, f"{reverse('login')}?next={reverse('usuarios:senha')}")

    def test_admin_define_senha_de_outra_pessoa_pede_troca(self):
        self.client.force_login(self.admin)
        r = self.client.post(reverse("usuarios:editar", args=[self.comum.pk]), {
            "first_name": "Ori", "last_name": "Entador", "email": "ori@t.local", "perfil": "orientador",
            "is_active": "on", "nova_senha": SENHA_PROVISORIA,
        })
        self.assertEqual(r.status_code, 302, getattr(r, "context", None) and r.context["form"].errors)
        self.comum.refresh_from_db()
        self.assertTrue(self.comum.precisa_trocar_senha)

    def test_admin_trocando_a_propria_senha_pelo_cadastro_nao_e_forcado(self):
        self.client.force_login(self.admin)
        r = self.client.post(reverse("usuarios:editar", args=[self.admin.pk]), {
            "first_name": "Adm", "last_name": "Inistrador", "email": "adm@t.local", "perfil": "administrador",
            "is_active": "on", "nova_senha": SENHA_NOVA,
        })
        self.assertEqual(r.status_code, 302, getattr(r, "context", None) and r.context["form"].errors)
        self.admin.refresh_from_db()
        self.assertFalse(self.admin.precisa_trocar_senha)


class BuscaAoVivoTests(TestCase):
    def test_listas_tem_busca_ao_vivo(self):
        adm = Usuario.objects.create_user("adm", email="adm@t.local", password="x", perfil=P.ADMINISTRADOR)
        self.client.force_login(adm)
        for nome in ("alunos:lista", "encontros:lista", "usuarios:lista"):
            r = self.client.get(reverse(nome))
            self.assertContains(r, 'data-busca-ao-vivo="#resultados"')
            self.assertContains(r, 'id="resultados"')
            self.assertContains(r, "js/busca_ao_vivo.js")

    def test_link_de_trocar_senha_no_topo(self):
        adm = Usuario.objects.create_user("adm", email="adm@t.local", password="x", perfil=P.ADMINISTRADOR)
        self.client.force_login(adm)
        self.assertContains(self.client.get(reverse("home")), reverse("usuarios:senha"))
