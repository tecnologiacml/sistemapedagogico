"""Leitura, validação e gravação de alunos a partir de CSV.

Fluxo: criar_previa() valida tudo SEM gravar alunos -> confirmar() grava linha a linha.
Cada linha é gravada isolada: se uma falhar, as outras continuam e o motivo fica no log.
"""
import csv
import io
import logging
import re
import unicodedata
from datetime import date, datetime

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone

from apps.alunos.models import Aluno, Responsavel

from .models import Importacao, ImportacaoLinha

logger = logging.getLogger(__name__)

TAMANHO_MAXIMO = 5 * 1024 * 1024
LINHAS_MAXIMAS = 5000
FORMATOS_DATA = ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y")


class ArquivoInvalido(Exception):
    """Problema que impede ler o arquivo inteiro. A mensagem já é para o usuário."""


# ---------- utilitários ----------
def sem_acento(texto):
    return unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()


def chave_nome(nome):
    return re.sub(r"\s+", " ", sem_acento(nome)).strip().upper()


def _cabecalho(texto):
    return re.sub(r"[^a-z0-9]+", " ", sem_acento(texto).lower()).strip()


ALIAS_ALUNO = {
    "nome": {"aluno", "nome", "nome do aluno", "nome completo"},
    "data_nascimento": {"data de nascimento", "data nascimento", "nascimento", "data nasc", "dt nascimento"},
    "ra": {"ra", "r a", "registro do aluno", "registro do aluno ra"},
    "matricula": {"matricula", "n matricula", "numero da matricula"},
    "serie": {"serie", "ano serie", "serie ano"},
    "celular": {"celular", "telefone", "celular do aluno", "telefone do aluno"},
    "email": {"email", "e mail", "email do aluno"},
    "endereco": {"endereco"},
    "bairro": {"bairro"},
    "cidade": {"cidade"},
    "cep": {"cep"},
    "unidade": {"unidade", "unidade do aluno"},
}


def _campo_do_cabecalho(h):
    palavras = set(h.split())
    if "responsavel" in palavras:
        if "idade" in palavras:
            return None
        if "email" in palavras or {"e", "mail"} <= palavras:
            return "resp_email"
        if "celular" in palavras or "telefone" in palavras:
            return "resp_celular"
        if "cep" in palavras:
            return "resp_cep"
        if "endereco" in palavras:
            return "resp_endereco"
        if "bairro" in palavras:
            return "resp_bairro"
        if "nascimento" in palavras or "nasc" in palavras:
            return "resp_data_nascimento"
        return "resp_nome"
    for campo, apelidos in ALIAS_ALUNO.items():
        if h in apelidos:
            return campo
    return None


# ---------- leitura do arquivo ----------
def ler_csv(conteudo):
    """Devolve (linhas, colunas_ignoradas). linhas = [(numero_da_linha, {campo: valor})]."""
    if len(conteudo) > TAMANHO_MAXIMO:
        raise ArquivoInvalido("O arquivo passa de 5 MB.")
    for codificacao in ("utf-8-sig", "cp1252"):
        try:
            texto = conteudo.decode(codificacao)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ArquivoInvalido("Não foi possível ler os caracteres do arquivo. Salve como CSV UTF-8.")

    if not texto.strip():
        raise ArquivoInvalido("O arquivo está vazio.")
    primeira = texto.splitlines()[0]
    delimitador = max((";", ",", "\t"), key=primeira.count)
    if primeira.count(delimitador) == 0:
        raise ArquivoInvalido("Não encontrei colunas. Confira se o arquivo é um CSV com cabeçalho.")

    leitor = csv.reader(io.StringIO(texto), delimiter=delimitador)
    cabecalho = next(leitor)
    mapa, ignoradas = {}, []
    for idx, original in enumerate(cabecalho):
        campo = _campo_do_cabecalho(_cabecalho(original))
        if campo and campo not in mapa.values():
            mapa[idx] = campo
        elif original.strip():
            ignoradas.append(original.strip())

    faltando = [rotulo for campo, rotulo in (("nome", "Aluno (nome)"), ("data_nascimento", "Data de nascimento"))
                if campo not in mapa.values()]
    if faltando:
        raise ArquivoInvalido("Colunas obrigatórias não encontradas no cabeçalho: " + ", ".join(faltando) + ".")

    linhas = []
    for bruta in leitor:
        if not any(c.strip() for c in bruta):
            continue  # linha totalmente vazia
        valores = {campo: (bruta[idx].strip() if idx < len(bruta) else "") for idx, campo in mapa.items()}
        linhas.append((leitor.line_num, valores))
        if len(linhas) > LINHAS_MAXIMAS:
            raise ArquivoInvalido(f"O arquivo tem mais de {LINHAS_MAXIMAS} linhas. Divida em arquivos menores.")
    if not linhas:
        raise ArquivoInvalido("O arquivo tem cabeçalho, mas nenhuma linha de aluno.")
    return linhas, ignoradas


# ---------- validação de campos ----------
def _data(texto):
    """(date|None, erro|None). Em branco devolve (None, None)."""
    texto = (texto or "").strip()
    if not texto:
        return None, None
    token = texto.split()[0]
    for formato in FORMATOS_DATA:
        try:
            d = datetime.strptime(token, formato).date()
        except ValueError:
            continue
        if d > date.today():
            return None, "data no futuro"
        if d.year < 1900:
            return None, "data anterior a 1900"
        return d, None
    return None, "formato inválido (use DD/MM/AAAA)"


def _codigo(texto):
    return re.sub(r"\.0$", "", (texto or "").strip())  # Excel grava 123 como 123.0


def _celular(texto):
    d = re.sub(r"\D", "", texto or "")
    if len(d) in (12, 13) and d.startswith("55"):
        d = d[2:]
    return d if len(d) in (10, 11) else None  # None = inválido


def _cep(texto):
    d = re.sub(r"\D", "", texto or "")
    return f"{d[:5]}-{d[5:]}" if len(d) == 8 else None


def _email_valido(email):
    try:
        validate_email(email)
        return len(email) <= 255
    except ValidationError:
        return False


def validar_campos(bruto):
    """Devolve (dados_limpos, erros, avisos). erro = rejeita a linha; aviso = importa sem o campo."""
    erros, avisos, d = [], [], {}

    nome = re.sub(r"\s+", " ", bruto.get("nome", "")).strip()
    if not nome:
        erros.append("Nome do aluno em branco")
    elif len(nome) > 255:
        erros.append("Nome do aluno com mais de 255 caracteres")
    d["nome"] = nome

    nasc_txt = bruto.get("data_nascimento", "")
    nasc, problema = _data(nasc_txt)
    if not nasc_txt.strip():
        erros.append("Data de nascimento em branco")
    elif problema:
        erros.append(f"Data de nascimento inválida: {problema}")
    d["data_nascimento"] = nasc.isoformat() if nasc else ""

    for campo, rotulo in (("ra", "R.A."), ("matricula", "Matrícula")):
        v = _codigo(bruto.get(campo, ""))
        if v and not re.fullmatch(r"[A-Za-z0-9._-]{1,50}", v):
            erros.append(f"{rotulo} inválido (use só letras, números, ponto, hífen; até 50 caracteres)")
            v = ""
        d[campo] = v

    email = (bruto.get("email") or "").strip().lower()
    if email and not _email_valido(email):
        erros.append("E-mail do aluno inválido")
        email = ""
    d["email"] = email

    cel = bruto.get("celular", "")
    d["celular"] = _celular(cel) or ""
    if cel.strip() and not d["celular"]:
        avisos.append("Celular do aluno inválido (não importado)")

    cep = bruto.get("cep", "")
    d["cep"] = _cep(cep) or ""
    if cep.strip() and not d["cep"]:
        avisos.append("CEP do aluno inválido (não importado)")

    for campo in ("endereco", "bairro", "cidade", "serie"):
        d[campo] = (bruto.get(campo) or "").strip()[: 50 if campo == "serie" else 255]

    # responsável
    campos_resp = ("resp_email", "resp_celular", "resp_cep", "resp_endereco", "resp_bairro", "resp_data_nascimento")
    rnome = re.sub(r"\s+", " ", bruto.get("resp_nome", "")).strip()
    d["resp_nome"] = rnome[:255]
    outros = any(bruto.get(c, "").strip() for c in campos_resp)
    if not rnome:
        if outros:
            avisos.append("Dados do responsável ignorados: nome do responsável em branco")
        for c in campos_resp:
            d[c] = ""
    else:
        remail = (bruto.get("resp_email") or "").strip().lower()
        if remail and not _email_valido(remail):
            erros.append("E-mail do responsável inválido")
            remail = ""
        d["resp_email"] = remail
        rcel = bruto.get("resp_celular", "")
        d["resp_celular"] = _celular(rcel) or ""
        if rcel.strip() and not d["resp_celular"]:
            avisos.append("Celular do responsável inválido (não importado)")
        rcep = bruto.get("resp_cep", "")
        d["resp_cep"] = _cep(rcep) or ""
        if rcep.strip() and not d["resp_cep"]:
            avisos.append("CEP do responsável inválido (não importado)")
        rnasc, rprob = _data(bruto.get("resp_data_nascimento", ""))
        d["resp_data_nascimento"] = rnasc.isoformat() if rnasc else ""
        if rprob:
            avisos.append("Data de nascimento do responsável inválida (não importada)")
        d["resp_endereco"] = (bruto.get("resp_endereco") or "").strip()[:255]
        d["resp_bairro"] = (bruto.get("resp_bairro") or "").strip()[:255]
    return d, erros, avisos


# ---------- análise completa (sem gravar nada) ----------
def analisar(conteudo, atualizar_existentes):
    linhas, ignoradas = ler_csv(conteudo)

    existentes = list(Aluno.objects.values("id", "nome", "ra", "matricula", "data_nascimento"))
    por_ra = {a["ra"]: a for a in existentes if a["ra"]}
    por_matricula = {a["matricula"]: a for a in existentes if a["matricula"]}
    por_nome_nasc = {}
    for a in existentes:
        por_nome_nasc.setdefault((chave_nome(a["nome"]), a["data_nascimento"]), []).append(a)

    vistos_ra, vistos_matricula, vistos_nome_nasc = {}, {}, {}
    resultado = []
    for numero, bruto in linhas:
        d, erros, avisos = validar_campos(bruto)
        acao, aluno_id = "criar", None

        if d["nome"] and d["data_nascimento"]:
            nasc = date.fromisoformat(d["data_nascimento"])
            chave = (chave_nome(d["nome"]), nasc)
            ra, matricula = d["ra"], d["matricula"]

            # duplicidade dentro do próprio arquivo
            if ra and ra in vistos_ra:
                erros.append(f"R.A. repetido no arquivo (já aparece na linha {vistos_ra[ra]})")
            if matricula and matricula in vistos_matricula:
                erros.append(f"Matrícula repetida no arquivo (já aparece na linha {vistos_matricula[matricula]})")
            if chave in vistos_nome_nasc:
                erros.append(f"Aluno duplicado no arquivo (mesmo nome e data de nascimento da linha {vistos_nome_nasc[chave]})")

            # duplicidade contra o banco
            alvo = None
            motivo_dup = ""
            if ra and ra in por_ra:
                alvo = por_ra[ra]
                if chave_nome(alvo["nome"]) != chave_nome(d["nome"]):
                    erros.append(f"R.A. já cadastrado para outro nome (aluno nº {alvo['id']})")
                    alvo = None
                else:
                    motivo_dup = f"Aluno já cadastrado com este R.A. (nº {alvo['id']})"
            else:
                candidatos = por_nome_nasc.get(chave, [])
                if candidatos:
                    c = candidatos[0]
                    if ra and c["ra"] and c["ra"] != ra:
                        erros.append(
                            f"Mesmo nome e data de nascimento do aluno nº {c['id']}, mas com outro R.A. (possível erro ou homônimo)"
                        )
                    else:
                        alvo = c
                        motivo_dup = f"Aluno já cadastrado (mesmo nome e data de nascimento, nº {c['id']})"
            if alvo and not erros:
                if atualizar_existentes:
                    acao, aluno_id = "atualizar", alvo["id"]
                else:
                    erros.append(motivo_dup + '. Marque "Atualizar alunos já cadastrados" para alterá-lo')
            if matricula and matricula in por_matricula and (aluno_id != por_matricula[matricula]["id"]):
                erros.append(f"Matrícula já usada por outro aluno (nº {por_matricula[matricula]['id']})")

            if not erros:  # só linhas boas "reservam" o valor para detectar repetidos depois
                if ra:
                    vistos_ra[ra] = numero
                if matricula:
                    vistos_matricula[matricula] = numero
                vistos_nome_nasc[chave] = numero

        resultado.append({
            "numero": numero, "nome": d["nome"], "ra": d["ra"], "dados": d,
            "erros": erros, "avisos": avisos, "acao": acao, "aluno_id": aluno_id,
        })
    return resultado, ignoradas


@transaction.atomic
def criar_previa(usuario, nome_arquivo, conteudo, unidade, atualizar_existentes):
    resultado, ignoradas = analisar(conteudo, atualizar_existentes)
    
    if not unidade:
        unidade = Aluno.Unidade.CENTRO

    imp = Importacao.objects.create(
        usuario=usuario, arquivo_nome=nome_arquivo[:255], unidade=unidade,
        atualizar_existentes=atualizar_existentes, colunas_ignoradas=", ".join(ignoradas),
        total_linhas=len(resultado),
    )
    novas = []
    for r in resultado:
        com_erro = bool(r["erros"])
        dados = {} if com_erro else {**r["dados"], "_acao": r["acao"], "_aluno_id": r["aluno_id"]}
        novas.append(ImportacaoLinha(
            importacao=imp, numero_linha=r["numero"], nome=r["nome"][:255], ra=r["ra"][:50],
            situacao=ImportacaoLinha.Situacao.ERRO if com_erro else ImportacaoLinha.Situacao.VALIDA,
            motivo="; ".join(r["erros"]), aviso="; ".join(r["avisos"]), dados=dados,
        ))
    ImportacaoLinha.objects.bulk_create(novas)
    imp.total_erros = sum(1 for r in resultado if r["erros"])
    imp.total_validas = imp.total_linhas - imp.total_erros
    imp.save(update_fields=["total_erros", "total_validas"])
    return imp


# ---------- gravação ----------
def _vazio_para_none(valor):
    return valor if valor not in ("", None) else None


def _auditoria(kwargs, usuario, criando):
    campos = {f.name for f in Aluno._meta.get_fields()}
    if criando and "created_by" in campos:
        kwargs["created_by"] = usuario
    if "updated_by" in campos:
        kwargs["updated_by"] = usuario


def _obter_responsavel(d, usuario):
    if not d.get("resp_nome"):
        return None
    qs = Responsavel.objects.filter(nome__iexact=d["resp_nome"])
    if d.get("resp_email"):
        qs = qs.filter(email__iexact=d["resp_email"])
    elif d.get("resp_celular"):
        qs = qs.filter(celular=d["resp_celular"])
    existente = qs.first()
    if existente:
        return existente
    dados = dict(
        nome=d["resp_nome"], email=_vazio_para_none(d["resp_email"]),
        celular=_vazio_para_none(d["resp_celular"]),
        data_nascimento=date.fromisoformat(d["resp_data_nascimento"]) if d.get("resp_data_nascimento") else None,
        endereco=_vazio_para_none(d["resp_endereco"]), bairro=_vazio_para_none(d["resp_bairro"]),
        cep=_vazio_para_none(d["resp_cep"]),
    )
    campos = {f.name for f in Responsavel._meta.get_fields()}
    if "created_by" in campos:
        dados["created_by"] = usuario
    return Responsavel.objects.create(**dados)


def _gravar(d, importacao, usuario):
    responsavel = _obter_responsavel(d, usuario)
    campos = {
        "nome": d["nome"], "data_nascimento": date.fromisoformat(d["data_nascimento"]),
        "ra": d["ra"], "matricula": d["matricula"], "celular": d["celular"], "email": d["email"],
        "endereco": d["endereco"], "bairro": d["bairro"], "cidade": d["cidade"],
        "cep": d["cep"], "serie": d["serie"],
    }
    if d["_acao"] == "atualizar":
        aluno = Aluno.objects.get(pk=d["_aluno_id"])
        for chave, valor in campos.items():
            if valor not in ("", None):
                setattr(aluno, chave, valor)
        if responsavel:
            aluno.responsavel = responsavel
        extra = {}
        _auditoria(extra, usuario, criando=False)
        for chave, valor in extra.items():
            setattr(aluno, chave, valor)
        aluno.save()
        return aluno, False
    extra = {}
    _auditoria(extra, usuario, criando=True)
    aluno = Aluno(
        unidade=importacao.unidade, responsavel=responsavel,
        **{k: _vazio_para_none(v) for k, v in campos.items()}, **extra,
    )
    aluno.save()
    return aluno, True


def confirmar(importacao, usuario):
    """Grava as linhas válidas. Devolve False se a importação já foi confirmada/cancelada."""
    travou = Importacao.objects.filter(pk=importacao.pk, status=Importacao.Status.PREVIA).update(
        status=Importacao.Status.PROCESSANDO
    )
    if not travou:  # clique duplo ou prévia já tratada
        return False

    S = ImportacaoLinha.Situacao
    criados = atualizados = falhas = 0
    for linha in importacao.linhas.filter(situacao=S.VALIDA).order_by("numero_linha"):
        try:
            with transaction.atomic():
                aluno, criado = _gravar(linha.dados, importacao, usuario)
        except Exception:  # noqa: BLE001 - qualquer falha isola só esta linha
            logger.exception("Falha ao gravar linha %s da importação %s", linha.numero_linha, importacao.pk)
            linha.situacao = S.REJEITADO
            linha.motivo = "Erro ao gravar no banco de dados (conflito com outro registro). A linha não foi importada."
            falhas += 1
        else:
            linha.situacao = S.CRIADO if criado else S.ATUALIZADO
            linha.aluno = aluno
            criados += criado
            atualizados += (not criado)
        linha.dados = {}  # não guarda dados pessoais além do necessário
        linha.save(update_fields=["situacao", "motivo", "aluno", "dados"])

    importacao.qtd_criados = criados
    importacao.qtd_atualizados = atualizados
    importacao.qtd_rejeitados = importacao.total_erros + falhas
    importacao.status = Importacao.Status.CONCLUIDA
    importacao.concluido_em = timezone.now()
    importacao.save()
    return True


def cancelar(importacao):
    if importacao.status != Importacao.Status.PREVIA:
        return False
    importacao.linhas.update(dados={})
    importacao.status = Importacao.Status.CANCELADA
    importacao.concluido_em = timezone.now()
    importacao.save(update_fields=["status", "concluido_em"])
    return True


MODELO_CSV = (
    "Aluno;Data de nascimento;RA;Matrícula;Série;Celular;Email;Endereço;Bairro;Cidade;CEP;"
    "Responsável financeiro;Email do responsável;Celular do responsável;"
    "Data de nascimento do responsável;CEP do responsável;Endereço do responsável;Bairro do responsável\r\n"
    "Maria Exemplo da Silva;15/03/2012;2026010001;123456;6º Ano EF;79999990000;maria@exemplo.com;"
    "Rua Exemplo 100;Centro;Itabaiana;49500-000;José Exemplo da Silva;jose@exemplo.com;79988880000;"
    "20/08/1980;49500-000;Rua Exemplo 100;Centro\r\n"
)