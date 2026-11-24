from datetime import date

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from apps.alunos.models import Aluno
from apps.usuarios.models import Usuario

from .models import AnoLetivo, Matricula, Serie, Turma, Unidade
from .services import MatriculaInvalida, matricular


class MatriculaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.centro = Unidade.objects.create(nome="Centro")
        cls.chiara = Unidade.objects.create(nome="Chiara")
        cls.a2026 = AnoLetivo.objects.create(ano=2026)
        cls.a2027 = AnoLetivo.objects.create(ano=2027)
        cls.s1 = Serie.objects.create(nome="1º Ano EF", ordem=1)
        cls.s2 = Serie.objects.create(nome="2º Ano EF", ordem=2)
        cls.t1a = Turma.objects.create(nome="1º ano A", unidade=cls.centro, ano_letivo=cls.a2026, serie=cls.s1)
        cls.t1b = Turma.objects.create(nome="1º ano B", unidade=cls.centro, ano_letivo=cls.a2026, serie=cls.s1)
        cls.t2a = Turma.objects.create(nome="2º ano A", unidade=cls.centro, ano_letivo=cls.a2027, serie=cls.s2)
        cls.t1c = Turma.objects.create(nome="1º ano C", unidade=cls.chiara, ano_letivo=cls.a2026, serie=cls.s1)
        cls.aluno = Aluno.objects.create(nome="Maria Silva", data_nascimento=date(2018, 5, 1), unidade="Centro")
        P = Usuario.Perfil
        cls.admin = Usuario.objects.create_user("adm", email="a@t.local", password="x", perfil=P.ADMINISTRADOR)
        cls.orientador = Usuario.objects.create_user("ori", email="o@t.local", password="x", perfil=P.ORIENTADOR)
        cls.gestor = Usuario.objects.create_user("ges", email="g@t.local", password="x", perfil=P.GESTOR)

    # --- regra de negócio ---
    def test_primeira_matricula(self):
        m = matricular(self.aluno, self.t1a, date(2026, 2, 1))
        self.assertEqual(m.situacao, "ativa")
        self.assertIsNone(m.data_fim)

    def test_trocar_de_turma_no_mesmo_ano_preserva_o_historico(self):
        matricular(self.aluno, self.t1a, date(2026, 2, 1))
        matricular(self.aluno, self.t1b, date(2026, 6, 1))
        self.assertEqual(self.aluno.matriculas.count(), 2)
        antiga = self.aluno.matriculas.get(turma=self.t1a)
        self.assertEqual(antiga.situacao, "transferida")
        self.assertEqual(antiga.data_fim, date(2026, 6, 1))
        self.assertEqual(self.aluno.matriculas.get(situacao="ativa").turma, self.t1b)

    def test_mudar_de_ano_preserva_o_historico(self):
        matricular(self.aluno, self.t1a, date(2026, 2, 1))
        matricular(self.aluno, self.t2a, date(2027, 2, 1))
        self.assertEqual(self.aluno.matriculas.count(), 2)
        self.assertEqual(self.aluno.matriculas.get(turma=self.t1a).situacao, "concluida")
        self.assertEqual(self.aluno.matriculas.get(situacao="ativa").turma, self.t2a)

    def test_nao_matricula_duas_vezes_na_mesma_turma(self):
        matricular(self.aluno, self.t1a, date(2026, 2, 1))
        with self.assertRaises(MatriculaInvalida):
            matricular(self.aluno, self.t1a, date(2026, 3, 1))
        self.assertEqual(self.aluno.matriculas.count(), 1)

    def test_data_anterior_ao_inicio_da_atual_e_recusada(self):
        matricular(self.aluno, self.t1a, date(2026, 2, 1))
        with self.assertRaises(MatriculaInvalida):
            matricular(self.aluno, self.t1b, date(2026, 1, 1))
        self.assertEqual(self.aluno.matriculas.get().situacao, "ativa")

    def test_banco_impede_duas_matriculas_ativas(self):
        Matricula.objects.create(aluno=self.aluno, turma=self.t1a)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Matricula.objects.create(aluno=self.aluno, turma=self.t1b)

    def test_matricula_mantem_unidade_e_serie_do_aluno_em_dia(self):
        matricular(self.aluno, self.t1c, date(2026, 2, 1))
        self.aluno.refresh_from_db()
        self.assertEqual((self.aluno.unidade, self.aluno.serie), ("Chiara", "1º Ano EF"))

    # --- tela ---
    def url(self):
        return reverse("turmas:matricular", args=[self.aluno.pk])

    def test_orientador_matricula_pela_tela(self):
        self.client.force_login(self.orientador)
        r = self.client.post(self.url(), {"turma": self.t1a.pk, "data_inicio": "2026-02-01"})
        self.assertRedirects(r, reverse("alunos:detalhe", args=[self.aluno.pk]))
        self.assertEqual(self.aluno.matriculas.get().turma, self.t1a)

    def test_quem_nao_edita_alunos_nao_matricula(self):
        self.client.force_login(self.gestor)
        self.assertEqual(self.client.get(self.url()).status_code, 403)
        r = self.client.post(self.url(), {"turma": self.t1a.pk, "data_inicio": "2026-02-01"})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.aluno.matriculas.count(), 0)

    def test_anonimo_vai_para_o_login(self):
        self.assertEqual(self.client.get(self.url()).status_code, 302)

    def test_turma_inativa_nao_aparece_para_escolha(self):
        Turma.objects.filter(pk=self.t1b.pk).update(ativa=False)
        self.client.force_login(self.admin)
        r = self.client.get(self.url())
        self.assertNotIn(self.t1b, r.context["form"].fields["turma"].queryset)
        self.assertIn(self.t1a, r.context["form"].fields["turma"].queryset)

    def test_tela_recusa_mesma_turma(self):
        matricular(self.aluno, self.t1a, date(2026, 2, 1))
        self.client.force_login(self.admin)
        r = self.client.post(self.url(), {"turma": self.t1a.pk, "data_inicio": "2026-03-01"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.aluno.matriculas.count(), 1)

    def test_ficha_mostra_o_historico(self):
        matricular(self.aluno, self.t1a, date(2026, 2, 1))
        matricular(self.aluno, self.t2a, date(2027, 2, 1))
        self.client.force_login(self.orientador)
        r = self.client.get(reverse("alunos:detalhe", args=[self.aluno.pk]))
        self.assertContains(r, "1º ano A")
        self.assertContains(r, "2º ano A")
        self.assertContains(r, "Concluída")

    def test_aluno_inexistente_da_404(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("turmas:matricular", args=[99999])).status_code, 404)
