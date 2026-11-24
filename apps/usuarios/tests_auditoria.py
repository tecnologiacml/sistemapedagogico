from django.contrib.admin.sites import site
from django.contrib.auth import authenticate
from django.test import RequestFactory, TestCase
from django.urls import reverse

from .admin import UsuarioAdmin
from .models import RegistroAuditoria as R
from .models import Usuario

SENHA = "Senha#Forte2026x"
NOVA = "Outra#Forte2027y"


class ContaDesativadaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.u = Usuario.objects.create_user(
            "maria", email="m@t.local", password=SENHA, perfil=Usuario.Perfil.ORIENTADOR, is_active=False
        )

    def test_conta_desativada_nao_autentica(self):
        self.assertIsNone(authenticate(username="maria", password=SENHA))

    def test_conta_desativada_nao_entra_pelo_login(self):
        r = self.client.post(reverse("login"), {"username": "maria", "password": SENHA})
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_sessao_aberta_cai_quando_a_conta_e_desativada(self):
        Usuario.objects.filter(pk=self.u.pk).update(is_active=True)
        self.client.force_login(self.u)
        self.assertEqual(self.client.get(reverse("home")).status_code, 200)
        Usuario.objects.filter(pk=self.u.pk).update(is_active=False)
        r = self.client.get(reverse("home"))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("login"), r["Location"])


class AuditoriaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        P = Usuario.Perfil
        cls.admin = Usuario.objects.create_user("adm", email="a@t.local", password=SENHA, perfil=P.ADMINISTRADOR)
        cls.ori = Usuario.objects.create_user(
            "ori", email="o@t.local", password=SENHA, perfil=P.ORIENTADOR, first_name="Ori", last_name="Entador"
        )

    def editar(self, **extra):
        dados = {"first_name": "Ori", "last_name": "Entador", "email": "o@t.local",
                 "perfil": "orientador", "is_active": "on"}
        dados.update(extra)
        return self.client.post(reverse("usuarios:editar", args=[self.ori.pk]), dados)

    def test_criar_usuario_registra(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("usuarios:criar"), {
            "first_name": "Ana", "last_name": "Lima", "username": "ana", "email": "ana@t.local",
            "perfil": "gestor", "password1": SENHA, "password2": SENHA,
        })
        reg = R.objects.get(alvo_username="ana")
        self.assertEqual(reg.acao, R.Acao.CRIADO)
        self.assertEqual(reg.feito_por, self.admin)
        self.assertTrue(any(m["campo"] == "Perfil" and m["depois"] == "Gestor pedagógico" for m in reg.alteracoes))

    def test_trocar_perfil_registra_antes_e_depois(self):
        self.client.force_login(self.admin)
        self.editar(perfil="gestor")
        reg = R.objects.get(alvo=self.ori, acao=R.Acao.ALTERADO)
        self.assertEqual(reg.feito_por_username, "adm")
        self.assertEqual(reg.alteracoes, [{"campo": "Perfil", "antes": "Orientador", "depois": "Gestor pedagógico"}])

    def test_desativar_conta_registra(self):
        self.client.force_login(self.admin)
        self.editar(is_active="")
        self.ori.refresh_from_db()
        self.assertFalse(self.ori.is_active)
        reg = R.objects.get(alvo=self.ori, acao=R.Acao.ALTERADO)
        self.assertEqual(reg.alteracoes, [{"campo": "Pode entrar no sistema", "antes": "Sim", "depois": "Não"}])

    def test_liberacao_extra_registra(self):
        self.client.force_login(self.admin)
        self.editar(perfil="gestor", permissoes_extras=["pode_editar_alunos"])
        reg = R.objects.get(alvo=self.ori, acao=R.Acao.ALTERADO)
        campos = {m["campo"]: m for m in reg.alteracoes}
        self.assertEqual(campos["Liberações extras"]["depois"], "Cadastrar e editar alunos")

    def test_salvar_sem_mudar_nada_nao_registra(self):
        self.client.force_login(self.admin)
        self.editar()
        self.assertEqual(R.objects.filter(alvo=self.ori).count(), 0)

    def test_senha_definida_pelo_admin_registra_sem_expor_a_senha(self):
        self.client.force_login(self.admin)
        self.editar(nova_senha=NOVA)
        reg = R.objects.get(alvo=self.ori, acao=R.Acao.SENHA_REDEFINIDA)
        self.assertEqual(reg.alteracoes, [])
        self.assertNotIn(NOVA, str(list(R.objects.values())))

    def test_troca_da_propria_senha_registra(self):
        self.client.force_login(self.ori)
        self.client.post(reverse("usuarios:senha"), {
            "old_password": SENHA, "new_password1": NOVA, "new_password2": NOVA,
        })
        reg = R.objects.get(alvo=self.ori)
        self.assertEqual(reg.acao, R.Acao.SENHA_ALTERADA)
        self.assertEqual(reg.feito_por, self.ori)

    def test_alteracao_pelo_django_admin_registra(self):
        ma = UsuarioAdmin(Usuario, site)
        req = RequestFactory().post("/")
        req.user = self.admin
        obj = Usuario.objects.get(pk=self.ori.pk)
        obj.perfil = "coordenacao"
        ma.save_model(req, obj, None, True)
        reg = R.objects.get(alvo=self.ori)
        self.assertEqual(reg.alteracoes[0]["depois"], "Coordenação")
        self.assertEqual(reg.feito_por, self.admin)

    def test_django_admin_nao_apaga_usuario(self):
        ma = UsuarioAdmin(Usuario, site)
        req = RequestFactory().post("/")
        req.user = self.admin
        self.assertFalse(ma.has_delete_permission(req, self.ori))

    def test_registro_sobrevive_a_remocao_da_conta(self):
        self.client.force_login(self.admin)
        self.editar(perfil="gestor")
        self.ori.delete()
        reg = R.objects.get(alvo_username="ori")
        self.assertIsNone(reg.alvo)

    # --- consulta do histórico ---
    def test_so_administrador_consulta_o_historico(self):
        self.client.force_login(self.ori)
        self.assertEqual(self.client.get(reverse("usuarios:auditoria")).status_code, 403)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("usuarios:auditoria")).status_code, 200)

    def test_historico_filtra_por_conta(self):
        self.client.force_login(self.admin)
        self.editar(perfil="gestor")
        outra = Usuario.objects.create_user("outra", email="x@t.local", password=SENHA)
        R.objects.create(alvo=outra, alvo_username="outra", acao=R.Acao.ALTERADO)
        r = self.client.get(reverse("usuarios:auditoria"), {"usuario": self.ori.pk})
        self.assertEqual({x.alvo_username for x in r.context["object_list"]}, {"ori"})
