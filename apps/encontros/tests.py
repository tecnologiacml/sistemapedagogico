from datetime import date

from django.test import TestCase
from django.urls import reverse

from apps.alunos.models import Aluno
from apps.usuarios.models import Usuario

from .models import Encontro


class EncontroTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        P = Usuario.Perfil
        cls.orient = Usuario.objects.create_user("orient", email="o@t.local", password="x", perfil=P.ORIENTADOR)
        cls.gestor = Usuario.objects.create_user("gestor", email="g@t.local", password="x", perfil=P.GESTOR)
        cls.aluno = Aluno.objects.create(
            ra="2026010002", nome="Alexya Parbhata Pereira Rosa", serie="3ª Série EM",
            cpf="52998224725", data_nascimento=date(2008, 1, 1),
        )

    def dados(self, **extra):
        d = {
            "aluno": self.aluno.pk, "data": "2026-11-17", "presente": "True", "duracao": "20-25",
            "temas": ["Estudos/aprendizagem", "Carreira"], "carreira_desejada": "Psicologia",
            "sabe_plurall": "0", "encaminhamento": "nao",
        }
        d.update(extra)
        return d

    def test_orientador_cria_primeiro_encontro(self):
        self.client.force_login(self.orient)
        r = self.client.post(reverse("encontros:criar"), self.dados())
        self.assertRedirects(r, reverse("encontros:lista"))
        e = Encontro.objects.get()
        self.assertEqual(e.numero, 1)
        self.assertEqual(e.combinados_anteriores, "primeiro")
        self.assertEqual(e.temas, ["Estudos/aprendizagem", "Carreira"])
        self.assertIs(e.sabe_plurall, False)
        self.assertEqual(e.registrado_por, self.orient)

    def test_numero_incrementa_e_exige_combinados(self):
        self.client.force_login(self.orient)
        self.client.post(reverse("encontros:criar"), self.dados())
        r = self.client.post(reverse("encontros:criar"), self.dados())
        self.assertEqual(r.status_code, 200)  # falta "combinados do encontro anterior"
        self.assertEqual(Encontro.objects.count(), 1)
        self.client.post(reverse("encontros:criar"), self.dados(combinados_anteriores="realizou"))
        self.assertEqual(list(Encontro.objects.order_by("numero").values_list("numero", flat=True)), [1, 2])

    def test_duracao_obrigatoria_se_presente(self):
        self.client.force_login(self.orient)
        r = self.client.post(reverse("encontros:criar"), self.dados(duracao=""))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Encontro.objects.count(), 0)

    def test_ausencia_nao_guarda_duracao_nem_temas(self):
        self.client.force_login(self.orient)
        self.client.post(reverse("encontros:criar"), self.dados(presente="False"))
        e = Encontro.objects.get()
        self.assertFalse(e.presente)
        self.assertEqual((e.duracao, e.temas), ("", []))

    def test_aluno_obrigatorio(self):
        self.client.force_login(self.orient)
        r = self.client.post(reverse("encontros:criar"), self.dados(aluno=""))
        self.assertEqual(r.status_code, 200)

    def test_gestor_nao_cria_mas_ve_lista(self):
        self.client.force_login(self.gestor)
        self.assertEqual(self.client.post(reverse("encontros:criar"), self.dados()).status_code, 403)
        self.assertEqual(self.client.get(reverse("encontros:lista")).status_code, 200)

    def test_busca_por_ra_e_nome(self):
        self.client.force_login(self.orient)
        for q in ("2026010002", "alexya"):
            r = self.client.get(reverse("encontros:buscar_aluno"), {"q": q})
            res = r.json()["resultados"]
            self.assertEqual(len(res), 1)
            self.assertEqual(res[0]["numero"], 1)
            self.assertEqual(res[0]["serie"], "3ª Série EM")

    def test_tela_de_novo_encontro_abre(self):
        self.client.force_login(self.orient)
        self.assertEqual(self.client.get(reverse("encontros:criar")).status_code, 200)

    def test_sem_login_vai_para_login(self):
        self.assertEqual(self.client.get(reverse("encontros:lista")).status_code, 302)
