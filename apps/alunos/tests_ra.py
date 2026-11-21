from datetime import date

from django.test import TestCase
from django.urls import reverse

from apps.usuarios.models import Usuario

from .models import Aluno


class RaUnicoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.orientador = Usuario.objects.create_user(
            "orient", email="o@t.local", password="x", perfil=Usuario.Perfil.ORIENTADOR
        )
        cls.existente = Aluno.objects.create(
            nome="Maria Silva", ra="RA123", data_nascimento=date(2010, 5, 1), unidade="Centro"
        )

    def setUp(self):
        self.client.force_login(self.orientador)

    def dados(self, **extra):
        d = {
            "nome": "João Souza", "data_nascimento": "2011-02-03",
            "unidade": "Centro", "responsavel_opcao": "nenhum", "ra": "RA999",
        }
        d.update(extra)
        return d

    def test_ra_novo_e_aceito(self):
        r = self.client.post(reverse("alunos:criar"), self.dados())
        self.assertRedirects(r, reverse("alunos:lista"))
        self.assertTrue(Aluno.objects.filter(ra="RA999").exists())

    def test_ra_duplicado_na_mesma_unidade_e_rejeitado_com_orientacao(self):
        r = self.client.post(reverse("alunos:criar"), self.dados(ra="RA123"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "já está cadastrado")
        self.assertContains(r, "Maria Silva")
        self.assertEqual(Aluno.objects.filter(ra="RA123").count(), 1)

    def test_ra_duplicado_em_outra_unidade_tambem_e_rejeitado(self):
        r = self.client.post(reverse("alunos:criar"), self.dados(ra="RA123", unidade="Chiara"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "já está cadastrado")
        self.assertEqual(Aluno.objects.count(), 1)

    def test_maiusculas_e_espacos_nao_burlam_a_regra(self):
        r = self.client.post(reverse("alunos:criar"), self.dados(ra="  ra123 "))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "já está cadastrado")
        self.assertEqual(Aluno.objects.count(), 1)

    def test_ra_e_salvo_em_maiusculas_sem_espacos_nas_pontas(self):
        self.client.post(reverse("alunos:criar"), self.dados(ra="  ab777 "))
        self.assertTrue(Aluno.objects.filter(ra="AB777").exists())

    def test_editar_mantendo_o_proprio_ra_funciona(self):
        r = self.client.post(
            reverse("alunos:editar", args=[self.existente.pk]),
            self.dados(nome="Maria S.", ra="RA123"),
        )
        self.assertRedirects(r, reverse("alunos:lista"))

    def test_nao_da_para_trocar_o_ra_por_um_de_outro_aluno(self):
        outro = Aluno.objects.create(
            nome="Pedro Lima", ra="RA555", data_nascimento=date(2010, 1, 1), unidade="Centro"
        )
        r = self.client.post(reverse("alunos:editar", args=[outro.pk]), self.dados(nome="Pedro Lima", ra="RA123"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "já está cadastrado")

    def test_varios_alunos_sem_ra_sao_permitidos(self):
        self.client.post(reverse("alunos:criar"), self.dados(nome="Sem Ra Um", ra=""))
        self.client.post(reverse("alunos:criar"), self.dados(nome="Sem Ra Dois", ra=""))
        self.assertEqual(Aluno.objects.filter(ra__isnull=True).count(), 2)
