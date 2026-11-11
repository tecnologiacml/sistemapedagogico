from django.test import TestCase
from django.urls import reverse

from .models import Usuario

P = Usuario.Perfil
SENHA = "Senha-Forte-2026"


class PerfilTests(TestCase):
    def test_permissoes_por_perfil(self):
        casos = {
            P.ADMINISTRADOR: (True, True, True),
            P.ORIENTADOR: (True, False, False),
            P.COORDENACAO: (False, False, False),
            P.GESTOR: (False, False, False),
        }
        for perfil, (edita, exclui, gerencia) in casos.items():
            u = Usuario.objects.create_user(f"u_{perfil}", email=f"{perfil}@t.local", password="x", perfil=perfil)
            self.assertEqual(u.pode_editar_alunos, edita, perfil)
            self.assertEqual(u.pode_excluir_alunos, exclui, perfil)
            self.assertEqual(u.pode_gerenciar_usuarios, gerencia, perfil)

    def test_superusuario_vira_administrador(self):
        u = Usuario.objects.create_superuser("root", email="root@t.local", password="x")
        self.assertEqual(u.perfil, P.ADMINISTRADOR)
        self.assertTrue(u.pode_gerenciar_usuarios)


class GestaoDeUsuariosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = Usuario.objects.create_user("adm", email="adm@t.local", password=SENHA, perfil=P.ADMINISTRADOR)
        cls.outros = {
            p: Usuario.objects.create_user(f"u_{p}", email=f"{p}@t.local", password=SENHA, perfil=p)
            for p in (P.ORIENTADOR, P.COORDENACAO, P.GESTOR)
        }

    def dados(self, **extra):
        d = {
            "first_name": "Ana", "last_name": "Lima", "username": "ana", "email": "Ana@Escola.com",
            "perfil": P.ORIENTADOR, "password1": SENHA, "password2": SENHA,
        }
        d.update(extra)
        return d

    def test_so_o_administrador_acessa_as_telas_de_usuarios(self):
        alvo = self.outros[P.ORIENTADOR]
        urls = [reverse("usuarios:lista"), reverse("usuarios:criar"), reverse("usuarios:editar", args=[alvo.pk])]
        for url in urls:  # anônimo vai para o login
            self.assertRedirects(self.client.get(url), f"{reverse('login')}?next={url}")
        for u in self.outros.values():
            self.client.force_login(u)
            for url in urls:
                self.assertEqual(self.client.get(url).status_code, 403)
            self.assertEqual(self.client.post(reverse("usuarios:criar"), self.dados()).status_code, 403)
        self.assertFalse(Usuario.objects.filter(username="ana").exists())
        self.client.force_login(self.admin)
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 200)

    def test_admin_cadastra_e_a_pessoa_consegue_entrar(self):
        self.client.force_login(self.admin)
        r = self.client.post(reverse("usuarios:criar"), self.dados())
        self.assertRedirects(r, reverse("usuarios:lista"))
        novo = Usuario.objects.get(username="ana")
        self.assertEqual((novo.email, novo.perfil, novo.is_active), ("ana@escola.com", P.ORIENTADOR, True))
        self.assertFalse(novo.is_superuser)
        self.client.logout()
        self.assertTrue(self.client.login(username="ana", password=SENHA))

    def test_senha_fraca_e_email_repetido_sao_rejeitados(self):
        self.client.force_login(self.admin)
        r = self.client.post(reverse("usuarios:criar"), self.dados(password1="123", password2="123"))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Usuario.objects.filter(username="ana").exists())
        r = self.client.post(reverse("usuarios:criar"), self.dados(email="ORIENTADOR@t.local"))
        self.assertContains(r, "Já existe um usuário com este e-mail")

    def test_perfil_nao_pode_ser_inventado(self):
        self.client.force_login(self.admin)
        r = self.client.post(reverse("usuarios:criar"), self.dados(perfil="superdono"))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Usuario.objects.filter(username="ana").exists())

    def test_usuario_inativo_nao_entra(self):
        alvo = self.outros[P.GESTOR]
        self.client.force_login(self.admin)
        r = self.client.post(reverse("usuarios:editar", args=[alvo.pk]), {
            "first_name": "G", "last_name": "T", "email": alvo.email, "perfil": alvo.perfil,
        })  # sem is_active marcado = desativa
        self.assertRedirects(r, reverse("usuarios:lista"))
        alvo.refresh_from_db()
        self.assertFalse(alvo.is_active)
        self.client.logout()
        self.assertFalse(self.client.login(username=alvo.username, password=SENHA))

    def test_editar_perfil_e_trocar_senha(self):
        alvo = self.outros[P.COORDENACAO]
        self.client.force_login(self.admin)
        r = self.client.post(reverse("usuarios:editar", args=[alvo.pk]), {
            "first_name": "C", "last_name": "T", "email": alvo.email, "perfil": P.ORIENTADOR,
            "is_active": "on", "nova_senha": "Outra-Senha-2026",
        })
        self.assertRedirects(r, reverse("usuarios:lista"))
        alvo.refresh_from_db()
        self.assertEqual(alvo.perfil, P.ORIENTADOR)
        self.assertTrue(alvo.check_password("Outra-Senha-2026"))

    def test_admin_nao_tira_o_proprio_acesso(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("usuarios:editar", args=[self.admin.pk]), {
            "first_name": "A", "last_name": "D", "email": self.admin.email, "perfil": P.GESTOR,
        })  # tenta virar gestor e se desativar
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.perfil, P.ADMINISTRADOR)
        self.assertTrue(self.admin.is_active)

    def test_nao_existe_cadastro_publico(self):
        for caminho in ("/cadastro/", "/registrar/", "/signup/", "/accounts/register/"):
            self.assertEqual(self.client.get(caminho).status_code, 404, caminho)
