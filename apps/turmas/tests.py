from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.usuarios.models import Usuario

from .models import AnoLetivo, Serie, Turma, Unidade


class TurmasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        hoje = timezone.localdate().year
        cls.centro = Unidade.objects.create(nome="Centro")
        cls.chiara = Unidade.objects.create(nome="Chiara")
        cls.ano_atual = AnoLetivo.objects.create(ano=hoje)
        cls.ano_passado = AnoLetivo.objects.create(ano=hoje - 1)
        cls.serie = Serie.objects.create(nome="6º ano", ordem=6)
        cls.t_passada = Turma.objects.create(
            nome="Turma A", unidade=cls.centro, ano_letivo=cls.ano_passado, serie=cls.serie
        )
        cls.t_atual = Turma.objects.create(
            nome="Turma A", unidade=cls.centro, ano_letivo=cls.ano_atual, serie=cls.serie
        )
        cls.t_chiara = Turma.objects.create(
            nome="Turma B", unidade=cls.chiara, ano_letivo=cls.ano_atual, serie=cls.serie
        )
        cls.admin = Usuario.objects.create_user(
            "adm", email="a@t.local", password="x", perfil=Usuario.Perfil.ADMINISTRADOR
        )
        cls.orientador = Usuario.objects.create_user(
            "ori", email="o@t.local", password="x", perfil=Usuario.Perfil.ORIENTADOR
        )

    def dados(self, **extra):
        d = {
            "nome": "Turma C", "serie": self.serie.pk, "unidade": self.centro.pk,
            "ano_letivo": self.ano_atual.pk, "ativa": "on",
        }
        d.update(extra)
        return d

    # --- acesso ---
    def test_anonimo_vai_para_o_login(self):
        url = reverse("turmas:lista")
        self.assertRedirects(self.client.get(url), f"{reverse('login')}?next={url}")

    def test_qualquer_perfil_logado_consulta_mas_so_admin_cadastra(self):
        self.client.force_login(self.orientador)
        self.assertEqual(self.client.get(reverse("turmas:lista")).status_code, 200)
        self.assertEqual(self.client.get(reverse("turmas:criar")).status_code, 403)
        self.assertEqual(self.client.post(reverse("turmas:criar"), self.dados()).status_code, 403)
        self.assertFalse(Turma.objects.filter(nome="Turma C").exists())

    # --- critério da US-007: anos distinguíveis e consulta respeita o ano ---
    def test_consulta_padrao_mostra_o_ano_corrente(self):
        self.client.force_login(self.orientador)
        r = self.client.get(reverse("turmas:lista"))
        self.assertEqual(set(r.context["object_list"]), {self.t_atual, self.t_chiara})

    def test_consulta_respeita_o_ano_selecionado(self):
        self.client.force_login(self.orientador)
        r = self.client.get(reverse("turmas:lista"), {"ano": self.ano_passado.pk})
        self.assertEqual(list(r.context["object_list"]), [self.t_passada])

    def test_todos_os_anos(self):
        self.client.force_login(self.orientador)
        r = self.client.get(reverse("turmas:lista"), {"ano": "todos"})
        self.assertEqual(r.context["paginator"].count, 3)

    def test_filtro_por_unidade(self):
        self.client.force_login(self.orientador)
        r = self.client.get(reverse("turmas:lista"), {"unidade": self.chiara.pk})
        self.assertEqual(list(r.context["object_list"]), [self.t_chiara])

    def test_ano_invalido_cai_no_padrao(self):
        self.client.force_login(self.orientador)
        r = self.client.get(reverse("turmas:lista"), {"ano": "lixo"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(set(r.context["object_list"]), {self.t_atual, self.t_chiara})

    # --- cadastro ---
    def test_admin_cadastra_turma(self):
        self.client.force_login(self.admin)
        r = self.client.post(reverse("turmas:criar"), self.dados())
        self.assertRedirects(r, reverse("turmas:lista"))
        self.assertTrue(Turma.objects.filter(nome="Turma C", ano_letivo=self.ano_atual).exists())

    def test_mesmo_nome_em_anos_diferentes_e_permitido(self):
        self.client.force_login(self.admin)
        r = self.client.post(
            reverse("turmas:criar"), self.dados(nome="Turma B", ano_letivo=self.ano_passado.pk, unidade=self.chiara.pk)
        )
        self.assertRedirects(r, reverse("turmas:lista"))

    def test_nome_repetido_na_mesma_unidade_e_ano_e_rejeitado(self):
        self.client.force_login(self.admin)
        r = self.client.post(reverse("turmas:criar"), self.dados(nome="Turma A"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Já existe uma turma")
        self.assertEqual(Turma.objects.filter(nome="Turma A", ano_letivo=self.ano_atual).count(), 1)

    def test_admin_edita_turma(self):
        self.client.force_login(self.admin)
        r = self.client.post(reverse("turmas:editar", args=[self.t_atual.pk]), self.dados(nome="Turma A1"))
        self.assertRedirects(r, reverse("turmas:lista"))
        self.t_atual.refresh_from_db()
        self.assertEqual(self.t_atual.nome, "Turma A1")
