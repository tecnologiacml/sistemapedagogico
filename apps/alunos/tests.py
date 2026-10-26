from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.usuarios.models import Usuario

from .models import Aluno
from .validators import validar_cpf

CPF_OK = "52998224725"  # CPF válido de exemplo


class CpfTests(TestCase):
    def test_cpf_valido(self):
        validar_cpf(CPF_OK)
        validar_cpf("529.982.247-25")

    def test_cpf_invalido(self):
        for ruim in ["52998224724", "11111111111", "123", ""]:
            with self.assertRaises(ValidationError):
                validar_cpf(ruim)


class AlunoViewsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        P = Usuario.Perfil
        cls.admin = Usuario.objects.create_user("adm", password="x", perfil=P.ADMINISTRADOR)
        cls.coord = Usuario.objects.create_user("coord", password="x", perfil=P.COORDENACAO)
        cls.prof = Usuario.objects.create_user("prof", password="x", perfil=P.PROFESSOR)
        cls.aluno = Aluno.objects.create(
            nome="Maria Silva", cpf=CPF_OK, data_nascimento=date(2010, 5, 1)
        )

    def dados(self, **extra):
        d = {"nome": "João  Souza", "cpf": "111.444.777-35", "data_nascimento": "2011-02-03"}
        d.update(extra)
        return d

    def test_anonimo_vai_para_login(self):
        r = self.client.get(reverse("alunos:lista"))
        self.assertRedirects(r, f"{reverse('login')}?next={reverse('alunos:lista')}")

    def test_professor_so_consulta(self):
        self.client.force_login(self.prof)
        self.assertEqual(self.client.get(reverse("alunos:lista")).status_code, 200)
        self.assertEqual(self.client.get(reverse("alunos:detalhe", args=[self.aluno.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("alunos:criar")).status_code, 403)
        self.assertEqual(self.client.post(reverse("alunos:criar"), self.dados()).status_code, 403)
        self.assertEqual(self.client.get(reverse("alunos:editar", args=[self.aluno.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse("alunos:excluir", args=[self.aluno.pk])).status_code, 403)
        self.assertTrue(Aluno.objects.filter(pk=self.aluno.pk).exists())

    def test_coordenacao_cria_e_edita_mas_nao_exclui(self):
        self.client.force_login(self.coord)
        r = self.client.post(reverse("alunos:criar"), self.dados())
        self.assertRedirects(r, reverse("alunos:lista"))
        novo = Aluno.objects.get(cpf="11144477735")
        self.assertEqual(novo.nome, "João Souza")  # espaços normalizados
        r = self.client.post(reverse("alunos:editar", args=[novo.pk]), self.dados(nome="João S."))
        self.assertRedirects(r, reverse("alunos:lista"))
        novo.refresh_from_db()
        self.assertEqual(novo.nome, "João S.")
        self.assertEqual(self.client.post(reverse("alunos:excluir", args=[novo.pk])).status_code, 403)

    def test_admin_exclui(self):
        self.client.force_login(self.admin)
        r = self.client.post(reverse("alunos:excluir", args=[self.aluno.pk]))
        self.assertRedirects(r, reverse("alunos:lista"))
        self.assertFalse(Aluno.objects.exists())

    def test_cpf_invalido_e_duplicado_sao_rejeitados(self):
        self.client.force_login(self.coord)
        r = self.client.post(reverse("alunos:criar"), self.dados(cpf="123.456.789-00"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "CPF inválido")
        r = self.client.post(reverse("alunos:criar"), self.dados(cpf=CPF_OK))
        self.assertContains(r, "Já existe um aluno com este CPF")
        self.assertEqual(Aluno.objects.count(), 1)

    def test_busca_por_nome_e_cpf(self):
        self.client.force_login(self.prof)
        r = self.client.get(reverse("alunos:lista"), {"q": "maria"})
        self.assertContains(r, "Maria Silva")
        r = self.client.get(reverse("alunos:lista"), {"q": "529.982"})
        self.assertContains(r, "Maria Silva")
        r = self.client.get(reverse("alunos:lista"), {"q": "zzz"})
        self.assertContains(r, "Nenhum aluno encontrado")

    def test_edicao_mantem_proprio_cpf(self):
        self.client.force_login(self.coord)
        r = self.client.post(
            reverse("alunos:editar", args=[self.aluno.pk]),
            {"nome": "Maria S.", "cpf": CPF_OK, "data_nascimento": "2010-05-01"},
        )
        self.assertRedirects(r, reverse("alunos:lista"))
