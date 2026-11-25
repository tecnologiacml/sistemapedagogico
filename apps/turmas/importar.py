"""Importação de matrículas por planilha (CSV): lê, confere e devolve uma prévia."""

import csv
import io
import unicodedata

from django.utils import timezone

from apps.alunos.models import Aluno

from .models import AnoLetivo, Matricula, Turma, Unidade

PREFIXO_PROVISORIA = "Sem turma definida"
LIMITE_LINHAS = 3000

OK, IGNORADO, ERRO = "ok", "ignorado", "erro"


class PlanilhaInvalida(Exception):
    pass


def normalizar(texto):
    """Minúsculas, sem acento, sem º/ª e com espaços simples: "1º Ano  A" e "1 ano a" ficam iguais."""
    texto = (texto or "").replace("º", "").replace("ª", "").replace("°", "")
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.lower().split())


def ler_planilha(conteudo):
    """Lê o CSV (UTF-8 ou Windows, separado por ; , ou tab) e devolve lista de dicts com colunas normalizadas."""
    try:
        texto = conteudo.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = conteudo.decode("latin-1")
    if not texto.strip():
        raise PlanilhaInvalida("A planilha está vazia.")
    primeira = texto.splitlines()[0]
    separador = max([";", ",", "\t"], key=primeira.count)
    leitor = csv.reader(io.StringIO(texto), delimiter=separador)
    cabecalho = [normalizar(c).replace(".", "") for c in next(leitor)]
    apelidos = {"r a": "ra", "registro": "ra", "aluno": "nome", "estudante": "nome", "ano letivo": "ano"}
    cabecalho = [apelidos.get(c, c) for c in cabecalho]
    if "turma" not in cabecalho or not ({"ra", "nome"} & set(cabecalho)):
        raise PlanilhaInvalida(
            "A planilha precisa ter a coluna \"turma\" e a coluna \"ra\" (ou \"nome\"). "
            "Colunas opcionais: unidade e ano."
        )
    linhas = []
    for numero, valores in enumerate(leitor, start=2):
        if not any(v.strip() for v in valores):
            continue
        linha = {c: (valores[i].strip() if i < len(valores) else "") for i, c in enumerate(cabecalho)}
        linha["_numero"] = numero
        linhas.append(linha)
    if len(linhas) > LIMITE_LINHAS:
        raise PlanilhaInvalida(f"A planilha tem mais de {LIMITE_LINHAS} linhas. Divida em partes.")
    if not linhas:
        raise PlanilhaInvalida("A planilha não tem nenhuma linha de aluno.")
    return linhas


def ano_padrao():
    hoje = timezone.localdate()
    return AnoLetivo.objects.filter(ano=hoje.year).first() or AnoLetivo.objects.first()


def validar(linhas):
    """Confere cada linha sem gravar nada. Devolve lista de resultados, um por linha."""
    padrao = ano_padrao()
    alunos_por_ra, alunos_por_nome = {}, {}
    for a in Aluno.objects.only("id", "nome", "ra", "unidade"):
        if a.ra:
            alunos_por_ra[a.ra.strip().upper()] = a
        alunos_por_nome.setdefault(normalizar(a.nome), []).append(a)
    ativas = dict(
        Matricula.objects.filter(situacao=Matricula.Situacao.ATIVA).values_list("aluno_id", "turma_id")
    )
    anos = {a.ano: a for a in AnoLetivo.objects.all()}
    unidades = {normalizar(u.nome): u for u in Unidade.objects.all()}
    turmas = {}
    for t in Turma.objects.filter(ativa=True).select_related("unidade", "ano_letivo"):
        turmas.setdefault((t.ano_letivo_id, t.unidade_id, normalizar(t.nome)), []).append(t)

    resultados, vistos = [], set()
    for linha in linhas:
        r = {
            "numero": linha["_numero"], "ra": linha.get("ra", ""), "nome": linha.get("nome", ""),
            "turma_texto": linha.get("turma", ""), "status": ERRO, "mensagem": "",
            "aluno_id": None, "turma_id": None, "turma_exibida": "",
        }
        resultados.append(r)

        # --- aluno ---
        aluno = None
        if linha.get("ra"):
            aluno = alunos_por_ra.get(linha["ra"].strip().upper())
            if not aluno:
                r["mensagem"] = "R.A. não encontrado."
                continue
        elif linha.get("nome"):
            candidatos = alunos_por_nome.get(normalizar(linha["nome"]), [])
            if not candidatos:
                r["mensagem"] = "Nenhum aluno com este nome."
                continue
            if len(candidatos) > 1:
                r["mensagem"] = "Há mais de um aluno com este nome. Use o R.A."
                continue
            aluno = candidatos[0]
        else:
            r["mensagem"] = "Linha sem R.A. e sem nome."
            continue
        r["aluno_id"], r["nome"] = aluno.pk, aluno.nome
        if aluno.pk in vistos:
            r["mensagem"] = "Este aluno aparece mais de uma vez na planilha."
            continue
        vistos.add(aluno.pk)

        # --- turma ---
        if not linha.get("turma"):
            r["mensagem"] = "Turma em branco."
            continue
        if linha.get("ano"):
            ano = anos.get(int(linha["ano"])) if linha["ano"].isdigit() else None
            if not ano:
                r["mensagem"] = f"Ano letivo \"{linha['ano']}\" não existe."
                continue
        else:
            ano = padrao
            if not ano:
                r["mensagem"] = "Não há ano letivo cadastrado."
                continue
        unidade = unidades.get(normalizar(linha.get("unidade") or aluno.unidade))
        if not unidade:
            r["mensagem"] = f"Unidade \"{linha.get('unidade') or aluno.unidade}\" não existe."
            continue
        achadas = turmas.get((ano.pk, unidade.pk, normalizar(linha["turma"])), [])
        if not achadas:
            r["mensagem"] = f"A turma \"{linha['turma']}\" não existe em {unidade.nome}, {ano.ano}."
            continue
        if len(achadas) > 1:
            r["mensagem"] = f"Mais de uma turma parecida com \"{linha['turma']}\" em {unidade.nome}, {ano.ano}."
            continue
        turma = achadas[0]
        r["turma_id"] = turma.pk
        r["turma_exibida"] = f"{ano.ano} · {unidade.nome} · {turma.nome}"
        if ativas.get(aluno.pk) == turma.pk:
            r["status"], r["mensagem"] = IGNORADO, "Já está matriculado nesta turma."
        else:
            r["status"] = OK
    return resultados
