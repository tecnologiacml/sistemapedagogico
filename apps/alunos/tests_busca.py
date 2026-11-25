from datetime import date

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.turmas.models import AnoLetivo, Serie, Turma, Unidade
from apps.turmas.services import matricular
from apps.usuarios.models import Usuario

from .models import Aluno


class BuscaEFiltrosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ano_corrente = timezone.localdate().year
        cls.centro = Unidade.objects.create(nome="Centro")
        cls.chiara = Unidade.objects.create(nome="Chiara")
        cls.a_atual = AnoLetivo.objects.create(ano=ano_corrente)
        cls.a_antigo = AnoLetivo.objects.create(ano=ano_corrente - 1)
        cls.s1 = Serie.objects.create(nome="1º Ano EF", ordem=1)
        cls.s2 = Serie.objects.create(nome="2º Ano EF", ordem=2)
        cls.t1a = Turma.objects.create(nome="1º ano A", unidade=cls.centro, ano_letivo=cls.a_atual, serie=cls.s1)
        cls.t1b = Turma.objects.create(nome="1º ano B", unidade=cls.centro, ano_letivo=cls.a_atual, serie=cls.s1)
        cls.t2a = Turma.objects.create(nome="2º ano A", unidade=cls.chiara, ano_letivo=cls.a_atual, serie=cls.s2)
        cls.t_velha = Turma.objects.create(nome="1º ano A", unidade=cls.centro, ano_letivo=cls.a_antigo, serie=cls.s1)

        def novo(nome, nasc, unidade, ra=None, cpf=None):
            return Aluno.objects.create(nome=nome, ra=ra, cpf=cpf, data_nascimento=nasc, unidade=unidade)

        cls.maria1 = novo("Maria Silva", date(2018, 3, 10), "Centro", ra="RA001")
        cls.maria2 = novo("Maria Silva", date(2017, 8, 22), "Chiara", ra="RA002")
        cls.joao = novo("João Souza", date(2018, 1, 1), "Centro", ra="RA003", cpf="52998224725")
        cls.ana = novo("Ana Lima", date(2018, 1, 1), "Centro")  # sem matrícula
        matricular(cls.maria1, cls.t1a, date(2026, 2, 1))
        matricular(cls.maria2, cls.t2a, date(2026, 2, 1))
        matricular(cls.joao, cls.t1b, date(2026, 2, 1))
        cls.user = Usuario.objects.create_user("ges", email="g@t.local", password="x", perfil=Usuario.Perfil.GESTOR)

    def setUp(self):
        self.client.force_login(self.user)

    def lista(self, **params):
        r = self.client.get(reverse("alunos:lista"), params)
        self.assertEqual(r.status_code, 200)
        return r, {a.pk for a in r.context["object_list"]}

    def test_anonimo_vai_para_o_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("alunos:lista")).status_code, 302)

    def test_sem_filtros_lista_todos(self):
        _, ids = self.lista()
        self.assertEqual(ids, {self.maria1.pk, self.maria2.pk, self.joao.pk, self.ana.pk})

    # --- filtros ---
    def test_filtro_por_unidade(self):
        _, ids = self.lista(unidade=self.chiara.pk)
        self.assertEqual(ids, {self.maria2.pk})

    def test_filtro_por_serie(self):
        _, ids = self.lista(serie=self.s1.pk)
        self.assertEqual(ids, {self.maria1.pk, self.joao.pk})

    def test_filtro_por_turma(self):
        _, ids = self.lista(turma=self.t1b.pk)
        self.assertEqual(ids, {self.joao.pk})

    def test_filtro_por_ano_letivo(self):
        _, ids = self.lista(ano=self.a_atual.pk)
        self.assertEqual(ids, {self.maria1.pk, self.maria2.pk, self.joao.pk})
        _, ids = self.lista(ano=self.a_antigo.pk)
        self.assertEqual(ids, set())

    def test_filtros_combinados(self):
        _, ids = self.lista(unidade=self.centro.pk, serie=self.s1.pk, ano=self.a_atual.pk)
        self.assertEqual(ids, {self.maria1.pk, self.joao.pk})
        _, ids = self.lista(unidade=self.chiara.pk, serie=self.s1.pk)
        self.assertEqual(ids, set())

    def test_filtro_vale_para_a_matricula_atual_e_nao_para_a_antiga(self):
        matricular(self.maria1, self.t1b, date(2026, 6, 1))  # sai da 1º ano A
        _, ids = self.lista(turma=self.t1a.pk)
        self.assertNotIn(self.maria1.pk, ids)
        _, ids = self.lista(turma=self.t1b.pk)
        self.assertEqual(ids, {self.maria1.pk, self.joao.pk})

    def test_valores_invalidos_sao_ignorados(self):
        _, ids = self.lista(ano="abc", unidade="", turma="x")
        self.assertEqual(len(ids), 4)

    # --- busca ---
    def test_busca_por_palavras_em_qualquer_ordem(self):
        _, ids = self.lista(q="silva maria")
        self.assertEqual(ids, {self.maria1.pk, self.maria2.pk})

    def test_busca_por_ra_e_por_cpf(self):
        _, ids = self.lista(q="RA003")
        self.assertEqual(ids, {self.joao.pk})
        _, ids = self.lista(q="529.982.247-25")
        self.assertEqual(ids, {self.joao.pk})

    def test_busca_combina_com_filtro(self):
        _, ids = self.lista(q="maria", unidade=self.chiara.pk)
        self.assertEqual(ids, {self.maria2.pk})

    # --- homônimos ---
    def test_homonimos_se_distinguem_na_lista(self):
        r, ids = self.lista(q="Maria Silva")
        self.assertEqual(len(ids), 2)
        self.assertContains(r, "Nasc. 10/03/2018")
        self.assertContains(r, "Nasc. 22/08/2017")
        self.assertContains(r, "1º ano A")
        self.assertContains(r, "2º ano A")
        self.assertContains(r, "Chiara")

    def test_aluno_sem_matricula_aparece_como_tal(self):
        r, _ = self.lista(q="Ana Lima")
        self.assertContains(r, "Sem matrícula")

    # --- tela ---
    def test_filtros_aparecem_selecionados(self):
        r, _ = self.lista(unidade=self.chiara.pk, serie=self.s2.pk)
        self.assertEqual(r.context["unidade_sel"], self.chiara.pk)
        self.assertEqual(r.context["serie_sel"], self.s2.pk)
        self.assertTrue(r.context["filtros_ativos"])

    def test_paginacao_mantem_os_filtros(self):
        for i in range(25):
            a = Aluno.objects.create(nome=f"Pedro {i:02d}", data_nascimento=date(2018, 1, 1), unidade="Centro")
            matricular(a, self.t1a, date(2026, 2, 1))
        r = self.client.get(reverse("alunos:lista"), {"unidade": self.centro.pk, "q": "pedro"})
        self.assertTrue(r.context["is_paginated"])
        self.assertContains(r, "unidade=")
        self.assertContains(r, "page=2")
