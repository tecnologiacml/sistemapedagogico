from django.test import TestCase

from .models import Usuario


class UsuarioTests(TestCase):
    def test_perfil_padrao_e_professor(self):
        u = Usuario.objects.create_user("prof", password="x")
        self.assertEqual(u.perfil, Usuario.Perfil.PROFESSOR)
        self.assertFalse(u.pode_editar_alunos)
        self.assertFalse(u.pode_excluir_alunos)

    def test_coordenacao_edita_mas_nao_exclui(self):
        u = Usuario.objects.create_user("c", password="x", perfil=Usuario.Perfil.COORDENACAO)
        self.assertTrue(u.pode_editar_alunos)
        self.assertFalse(u.pode_excluir_alunos)

    def test_superusuario_vira_administrador(self):
        u = Usuario.objects.create_superuser("root", password="x")
        self.assertEqual(u.perfil, Usuario.Perfil.ADMINISTRADOR)
        self.assertTrue(u.pode_excluir_alunos)
