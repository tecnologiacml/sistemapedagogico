from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.usuarios.models import Usuario

from .models import AnoLetivo, Serie, Turma, Unidade


class BuscaDeTurmasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        centro = Unidade.objects.create(nome="Centro")
        ano = AnoLetivo.objects.create(ano=timezone.localdate().year)
        s1 = Serie.objects.create(nome="1º Ano EF", ordem=1)
        cls.a = Turma.objects.create(nome="1º ano A", unidade=centro, ano_letivo=ano, serie=s1)
        cls.b = Turma.objects.create(nome="1º ano B", unidade=centro, ano_letivo=ano, serie=s1)
        cls.prov = Turma.objects.create(nome="Sem turma definida · 1º Ano EF", unidade=centro, ano_letivo=ano, serie=s1)
        cls.user = Usuario.objects.create_user("ges", email="g@t.local", password="x", perfil=Usuario.Perfil.GESTOR)

    def achados(self, q):
        self.client.force_login(self.user)
        r = self.client.get(reverse("turmas:lista"), {"q": q})
        return set(r.context["object_list"])

    def test_letra_da_turma_nao_acha_as_outras(self):
        self.assertEqual(self.achados("1º ano A"), {self.a})
        self.assertEqual(self.achados("1 ano a"), {self.a})
        self.assertEqual(self.achados("1º ano B"), {self.b})

    def test_so_a_letra(self):
        self.assertEqual(self.achados("b"), {self.b})

    def test_palavras_maiores_continuam_por_trecho(self):
        self.assertEqual(self.achados("1º ano"), {self.a, self.b, self.prov})
        self.assertEqual(self.achados("provis"), set())
        self.assertEqual(self.achados("definida"), {self.prov})

    def test_busca_pela_serie(self):
        self.assertEqual(self.achados("ano ef"), {self.a, self.b, self.prov})
