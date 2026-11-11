from django.test import TestCase
from django.urls import reverse

from apps.usuarios.models import Usuario


class InicioTests(TestCase):
    def test_anonimo_vai_para_o_login(self):
        self.assertRedirects(self.client.get(reverse("home")), f"{reverse('login')}?next=/")

    def test_tela_de_entrada_so_tem_a_identidade_e_o_menu(self):
        u = Usuario.objects.create_user("o", email="o@t.local", password="x")
        self.client.force_login(u)
        r = self.client.get(reverse("home"))
        self.assertContains(r, "Sistema Pedagógico")
        self.assertContains(r, "Dashboards")  # no menu lateral
        for removido in ("Buscar por aluno", "Alunos ativos", "Alunos por turma", "Mais do que ensinar", "Educação"):
            self.assertNotContains(r, removido)
        self.assertNotContains(r, "Usuários")  # item só do administrador

    def test_administrador_ve_usuarios_no_menu(self):
        a = Usuario.objects.create_superuser("a", email="a@t.local", password="x")
        self.client.force_login(a)
        self.assertContains(self.client.get(reverse("home")), reverse("usuarios:lista"))
