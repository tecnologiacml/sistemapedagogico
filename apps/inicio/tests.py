from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.alunos.models import Aluno
from apps.usuarios.models import Usuario


class InicioTests(TestCase):
    def test_anonimo_vai_para_o_login(self):
        self.assertRedirects(self.client.get(reverse("home")), f"{reverse('login')}?next=/")

    def test_tela_de_entrada_tem_os_paineis_e_o_menu(self):
        u = Usuario.objects.create_user("o", email="o@t.local", password="x")
        self.client.force_login(u)
        r = self.client.get(reverse("home"))
        self.assertContains(r, "Sistema Pedagógico")
        self.assertContains(r, "Calendário")
        self.assertContains(r, "Atividades Recentes")
        self.assertContains(r, "Aniversariantes da Semana")
        self.assertContains(r, "Dashboards")  # no menu lateral
        for removido in ("Buscar por aluno", "Alunos ativos", "Alunos por turma", "Mais do que ensinar", "Educação"):
            self.assertNotContains(r, removido)
        self.assertNotContains(r, "Usuários")  # item só do administrador

    def test_administrador_ve_usuarios_no_menu(self):
        a = Usuario.objects.create_superuser("a", email="a@t.local", password="x")
        self.client.force_login(a)
        self.assertContains(self.client.get(reverse("home")), reverse("usuarios:lista"))

    def test_aniversariante_de_hoje_aparece_sem_foto(self):
        u = Usuario.objects.create_user("o", email="o@t.local", password="x")
        self.client.force_login(u)
        hoje = timezone.localdate()
        Aluno.objects.create(nome="Maria Aniversariante", data_nascimento=hoje.replace(year=hoje.year - 10))
        r = self.client.get(reverse("home"))
        self.assertContains(r, "Maria Aniversariante")
        self.assertContains(r, "Hoje")
        self.assertNotContains(r, "<img")

    def test_aniversario_fora_dos_proximos_7_dias_nao_aparece(self):
        u = Usuario.objects.create_user("o", email="o@t.local", password="x")
        self.client.force_login(u)
        longe = timezone.localdate() + timedelta(days=20)
        Aluno.objects.create(nome="Joao Distante", data_nascimento=longe.replace(year=longe.year - 9))
        self.assertNotContains(self.client.get(reverse("home")), "Joao Distante")

    def test_mes_invalido_na_url_nao_quebra(self):
        u = Usuario.objects.create_user("o", email="o@t.local", password="x")
        self.client.force_login(u)
        self.assertEqual(self.client.get(reverse("home"), {"mes": "lixo"}).status_code, 200)