from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.alunos.models import Aluno
from apps.usuarios.models import Usuario

from . import importar
from .models import AnoLetivo, Matricula, Serie, Turma, Unidade
from .services import matricular, matricular_em_lote


def csv_bytes(texto, codificacao="utf-8"):
    return texto.encode(codificacao)


class BaseImportacao(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.centro = Unidade.objects.create(nome="Centro")
        cls.chiara = Unidade.objects.create(nome="Chiara")
        from django.utils import timezone
        cls.ano = AnoLetivo.objects.create(ano=timezone.localdate().year)
        cls.s_sem = Serie.objects.create(nome="Sem série", ordem=99)
        cls.s1 = Serie.objects.create(nome="1º Ano EF", ordem=1)
        cls.prov = Turma.objects.create(nome="Sem turma definida", unidade=cls.centro, ano_letivo=cls.ano, serie=cls.s_sem)
        cls.t1a = Turma.objects.create(nome="1º ano A", unidade=cls.centro, ano_letivo=cls.ano, serie=cls.s1)
        cls.t1b = Turma.objects.create(nome="1º ano B", unidade=cls.centro, ano_letivo=cls.ano, serie=cls.s1)
        cls.t1a_chiara = Turma.objects.create(nome="1º ano A", unidade=cls.chiara, ano_letivo=cls.ano, serie=cls.s1)
        cls.maria = Aluno.objects.create(nome="Maria Silva", ra="RA001", data_nascimento=date(2018, 1, 1), unidade="Centro")
        cls.joao = Aluno.objects.create(nome="João Souza", ra="RA002", data_nascimento=date(2018, 1, 1), unidade="Centro")
        cls.ana = Aluno.objects.create(nome="Ana Lima", data_nascimento=date(2018, 1, 1), unidade="Chiara")
        for a in (cls.maria, cls.joao):
            matricular(a, cls.prov, date(2026, 1, 10))
        P = Usuario.Perfil
        cls.ori = Usuario.objects.create_user("ori", email="o@t.local", password="x", perfil=P.ORIENTADOR)
        cls.ges = Usuario.objects.create_user("ges", email="g@t.local", password="x", perfil=P.GESTOR)


class LeituraEValidacaoTests(BaseImportacao):
    def validar(self, texto, **kw):
        return importar.validar(importar.ler_planilha(csv_bytes(texto, **kw)))

    def test_normalizar_ignora_acento_simbolo_e_caixa(self):
        self.assertEqual(importar.normalizar("1º  Ano A"), importar.normalizar("1 ano a"))
        self.assertEqual(importar.normalizar("Série"), "serie")

    def test_aceita_ponto_e_virgula_virgula_e_tab(self):
        for sep in (";", ",", "\t"):
            r = self.validar(f"ra{sep}turma\nRA001{sep}1º ano A\n")
            self.assertEqual(r[0]["status"], importar.OK, sep)

    def test_aceita_codificacao_windows(self):
        r = self.validar("ra;nome;turma\n;João Souza;1º ano A\n", codificacao="latin-1")
        self.assertEqual(r[0]["status"], importar.OK)
        self.assertEqual(r[0]["aluno_id"], self.joao.pk)

    def test_turma_escrita_de_outro_jeito_acha(self):
        r = self.validar("ra;turma\nra001;1 ANO a\n")
        self.assertEqual(r[0]["status"], importar.OK)
        self.assertEqual(r[0]["turma_id"], self.t1a.pk)

    def test_unidade_padrao_e_a_do_aluno(self):
        Aluno.objects.filter(pk=self.ana.pk).update(ra="RA003")
        r = self.validar("ra;turma\nRA003;1º ano A\n")
        self.assertEqual(r[0]["turma_id"], self.t1a_chiara.pk)

    def test_coluna_unidade_manda_sobre_a_do_aluno(self):
        r = self.validar("ra;turma;unidade\nRA001;1º ano A;Chiara\n")
        self.assertEqual(r[0]["turma_id"], self.t1a_chiara.pk)

    def test_erros_por_linha(self):
        r = self.validar(
            "ra;nome;turma;ano\n"
            "NAOEXISTE;;1º ano A;\n"
            ";;1º ano A;\n"
            "RA001;;turma fantasma;\n"
            "RA002;;;\n"
            ";Ana Lima;1º ano A;1999\n"
        )
        self.assertEqual([x["status"] for x in r], [importar.ERRO] * 5)
        self.assertIn("R.A. não encontrado", r[0]["mensagem"])
        self.assertIn("sem R.A. e sem nome", r[1]["mensagem"])
        self.assertIn("não existe", r[2]["mensagem"])
        self.assertIn("Turma em branco", r[3]["mensagem"])
        self.assertIn("Ano letivo", r[4]["mensagem"])

    def test_nome_repetido_exige_ra(self):
        Aluno.objects.create(nome="Maria Silva", data_nascimento=date(2018, 1, 1), unidade="Centro")
        r = self.validar("nome;turma\nMaria Silva;1º ano A\n")
        self.assertEqual(r[0]["status"], importar.ERRO)
        self.assertIn("mais de um aluno", r[0]["mensagem"])

    def test_aluno_repetido_na_planilha(self):
        r = self.validar("ra;turma\nRA001;1º ano A\nRA001;1º ano B\n")
        self.assertEqual(r[0]["status"], importar.OK)
        self.assertEqual(r[1]["status"], importar.ERRO)

    def test_ja_na_turma_e_ignorado(self):
        matricular(self.maria, self.t1a, date(2026, 3, 1))
        r = self.validar("ra;turma\nRA001;1º ano A\n")
        self.assertEqual(r[0]["status"], importar.IGNORADO)

    def test_planilha_sem_colunas_obrigatorias(self):
        with self.assertRaises(importar.PlanilhaInvalida):
            importar.ler_planilha(csv_bytes("nome;serie\nMaria;1\n"))
        with self.assertRaises(importar.PlanilhaInvalida):
            importar.ler_planilha(csv_bytes(""))
        with self.assertRaises(importar.PlanilhaInvalida):
            importar.ler_planilha(csv_bytes("ra;turma\n"))


class LoteTests(BaseImportacao):
    def test_lote_faz_o_mesmo_que_matricular_um_a_um(self):
        aplicadas, ignoradas = matricular_em_lote(
            [(self.maria, self.t1a), (self.joao, self.t1b)], date(2026, 2, 1)
        )
        self.assertEqual((aplicadas, ignoradas), (2, 0))
        for aluno, turma in ((self.maria, self.t1a), (self.joao, self.t1b)):
            self.assertEqual(aluno.matriculas.count(), 2)
            self.assertEqual(aluno.matriculas.get(situacao="ativa").turma, turma)
            antiga = aluno.matriculas.get(turma=self.prov)
            self.assertEqual((antiga.situacao, antiga.data_fim), ("transferida", date(2026, 2, 1)))
            aluno.refresh_from_db()
            self.assertEqual((aluno.unidade, aluno.serie), ("Centro", "1º Ano EF"))

    def test_lote_ignora_quem_ja_esta_na_turma_ou_data_anterior(self):
        aplicadas, ignoradas = matricular_em_lote(
            [(self.maria, self.prov), (self.joao, self.t1a)], date(2026, 1, 1)
        )
        self.assertEqual((aplicadas, ignoradas), (0, 2))
        self.assertEqual(Matricula.objects.filter(situacao="ativa").count(), 2)


class TelaImportacaoTests(BaseImportacao):
    url = property(lambda s: reverse("turmas:importar_matriculas"))

    def enviar(self, texto, data="2026-02-01"):
        arq = SimpleUploadedFile("m.csv", csv_bytes(texto), content_type="text/csv")
        return self.client.post(self.url, {"arquivo": arq, "data_inicio": data})

    def test_previa_nao_grava_nada(self):
        self.client.force_login(self.ori)
        r = self.enviar("ra;turma\nRA001;1º ano A\nRA002;1º ano B\nXX;1º ano A\n")
        self.assertEqual(r.status_code, 200)
        self.assertEqual((r.context["n_ok"], r.context["n_erros"]), (2, 1))
        self.assertEqual(Matricula.objects.count(), 2)  # só as provisórias da preparação

    def test_confirmar_aplica_e_preserva_historico(self):
        self.client.force_login(self.ori)
        self.enviar("ra;turma\nRA001;1º ano A\nRA002;1º ano B\n")
        r = self.client.post(self.url, {"confirmar": "1"})
        self.assertRedirects(r, reverse("turmas:lista"))
        self.assertEqual(self.maria.matriculas.get(situacao="ativa").turma, self.t1a)
        self.assertEqual(self.joao.matriculas.get(situacao="ativa").turma, self.t1b)
        self.assertEqual(self.maria.matriculas.count(), 2)  # a provisória continua no histórico

    def test_confirmar_aplica_so_as_validas(self):
        self.client.force_login(self.ori)
        self.enviar("ra;turma\nRA001;1º ano A\nXX;1º ano A\n")
        self.client.post(self.url, {"confirmar": "1"})
        self.assertEqual(self.maria.matriculas.get(situacao="ativa").turma, self.t1a)
        self.assertEqual(self.joao.matriculas.get(situacao="ativa").turma, self.prov)

    def test_confirmar_sem_previa_nao_faz_nada(self):
        self.client.force_login(self.ori)
        r = self.client.post(self.url, {"confirmar": "1"})
        self.assertRedirects(r, self.url)
        self.assertEqual(Matricula.objects.count(), 2)

    def test_confirmar_duas_vezes_nao_duplica(self):
        self.client.force_login(self.ori)
        self.enviar("ra;turma\nRA001;1º ano A\n")
        self.client.post(self.url, {"confirmar": "1"})
        self.client.post(self.url, {"confirmar": "1"})
        self.assertEqual(self.maria.matriculas.count(), 2)

    def test_arquivo_que_nao_e_csv_e_recusado(self):
        self.client.force_login(self.ori)
        arq = SimpleUploadedFile("m.xlsx", b"x", content_type="application/octet-stream")
        r = self.client.post(self.url, {"arquivo": arq, "data_inicio": "2026-02-01"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context["form"].errors["arquivo"])

    def test_planilha_sem_colunas_mostra_erro_na_tela(self):
        self.client.force_login(self.ori)
        r = self.enviar("nome;serie\nMaria;1\n")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context["form"].errors["arquivo"])

    def test_quem_nao_edita_alunos_recebe_403(self):
        self.client.force_login(self.ges)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.enviar("ra;turma\nRA001;1º ano A\n").status_code, 403)
        self.assertEqual(self.client.get(reverse("turmas:alunos_sem_turma")).status_code, 403)

    def test_anonimo_vai_para_o_login(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_exporta_so_os_alunos_na_turma_provisoria(self):
        matricular(self.joao, self.t1a, date(2026, 3, 1))
        self.client.force_login(self.ori)
        r = self.client.get(reverse("turmas:alunos_sem_turma"))
        corpo = r.content.decode("utf-8-sig")
        self.assertEqual(r["Content-Type"].split(";")[0], "text/csv")
        self.assertIn("ra;nome;unidade;turma", corpo)
        self.assertIn("Maria Silva", corpo)
        self.assertNotIn("João Souza", corpo)

    def test_planilha_exportada_volta_como_entrada(self):
        self.client.force_login(self.ori)
        exportada = self.client.get(reverse("turmas:alunos_sem_turma")).content.decode("utf-8-sig")
        linhas = exportada.strip().splitlines()
        linhas = [linhas[0]] + [l + "1º ano A" for l in linhas[1:]]
        r = self.enviar("\n".join(linhas) + "\n")
        self.assertEqual((r.context["n_ok"], r.context["n_erros"]), (2, 0))
