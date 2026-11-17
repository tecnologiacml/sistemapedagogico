import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from . import services
from .forms import UploadCSVForm
from .models import Importacao, ImportacaoLinha
from apps.alunos.models import Aluno
from datetime import date, datetime
from django.utils import timezone


def calcular_idade(data_nascimento):
    """Calcula a idade a partir da data de nascimento."""

    if not data_nascimento:
        return "—"

    try:
        if isinstance(data_nascimento, str):
            data_nascimento = date.fromisoformat(data_nascimento)

        hoje = timezone.localdate()

        idade = hoje.year - data_nascimento.year

        if (hoje.month, hoje.day) < (
            data_nascimento.month,
            data_nascimento.day
        ):
            idade -= 1

        return idade if idade >= 0 else "—"

    except (ValueError, TypeError):
        return "—"


def atualizar_totais(imp):
    """Atualiza os totais da prévia após alterações."""

    S = ImportacaoLinha.Situacao

    imp.total_validas = imp.linhas.filter(
        situacao=S.VALIDA
    ).count()

    imp.total_erros = imp.linhas.filter(
        situacao=S.ERRO
    ).count()

    imp.save(update_fields=[
        "total_validas",
        "total_erros"
    ])


def validar_edicao(imp, linha, bruto):
    """Valida os dados editados antes de atualizar a prévia."""

    dados, erros, avisos = services.validar_campos(bruto)

    if erros:
        return None, erros

    aluno_id = linha.dados.get("_aluno_id")

    # Verifica se o R.A. já pertence a outro aluno.
    if dados["ra"]:
        qs = Aluno.objects.filter(ra=dados["ra"])

        if aluno_id:
            qs = qs.exclude(pk=aluno_id)

        if qs.exists():
            erros.append("Este R.A. já está cadastrado para outro aluno.")

    # Verifica se a matrícula já pertence a outro aluno.
    if dados["matricula"]:
        qs = Aluno.objects.filter(matricula=dados["matricula"])

        if aluno_id:
            qs = qs.exclude(pk=aluno_id)

        if qs.exists():
            erros.append("Esta matrícula já está cadastrada para outro aluno.")

    # Verifica duplicidades entre as linhas válidas desta importação.
    outras = imp.linhas.filter(
        situacao=ImportacaoLinha.Situacao.VALIDA
    ).exclude(pk=linha.pk)

    for outra in outras:
        outro = outra.dados

        if dados["ra"] and dados["ra"] == outro.get("ra"):
            erros.append("Este R.A. já aparece em outro aluno desta importação.")

        if (
            dados["matricula"]
            and dados["matricula"] == outro.get("matricula")
        ):
            erros.append("Esta matrícula já aparece em outro aluno desta importação.")

        if (
            dados["nome"].strip().upper() == outro.get("nome", "").strip().upper()
            and dados["data_nascimento"] == outro.get("data_nascimento")
        ):
            erros.append("Já existe um aluno com o mesmo nome e data de nascimento nesta importação.")

    if erros:
        return None, erros

    dados["_acao"] = linha.dados.get("_acao", "criar")
    dados["_aluno_id"] = aluno_id

    return {
        "dados": dados,
        "avisos": avisos,
    }, []

PERMISSAO = "importacao.importar_alunos"
S = ImportacaoLinha.Situacao


def protegida(view):
    return login_required(permission_required(PERMISSAO, raise_exception=True)(view))


@protegida
def importar(request):
    form = UploadCSVForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        arquivo = form.cleaned_data["arquivo"]
        try:
            imp = services.criar_previa(
    usuario=request.user,
    nome_arquivo=arquivo.name,
    conteudo=arquivo.read(),
    unidade=Aluno.Unidade.CENTRO,
    atualizar_existentes=form.cleaned_data["atualizar_existentes"],
)
        except services.ArquivoInvalido as exc:
            form.add_error("arquivo", str(exc))
        else:
            return redirect("importacao:previa", pk=imp.pk)
    return render(request, "importacao/importar.html", {"form": form})


@protegida
def previa(request, pk):

    imp = get_object_or_404(Importacao, pk=pk)

    if imp.status != Importacao.Status.PREVIA:
        return redirect("importacao:resultado", pk=imp.pk)

    S = ImportacaoLinha.Situacao

    if request.method == "POST":

        acao = request.POST.get("acao")

        # CANCELAR IMPORTAÇÃO
        if acao == "cancelar":

            services.cancelar(imp)

            messages.info(
                request,
                "Importação cancelada. Nenhum aluno foi cadastrado."
            )

            return redirect("importacao:importar")

        # EXCLUIR ALUNO DA PRÉVIA
        if acao == "excluir":

            linha = get_object_or_404(
                imp.linhas,
                pk=request.POST.get("linha_id"),
                situacao=S.VALIDA
            )

            linha.situacao = S.EXCLUIDO
            linha.dados = {}
            linha.save(update_fields=["situacao", "dados"])

            atualizar_totais(imp)

            messages.success(
                request,
                f"Aluno {linha.nome} removido da importação."
            )

            return redirect("importacao:previa", pk=imp.pk)

        # EDITAR ALUNO
        if acao == "editar":

            linha = get_object_or_404(
                imp.linhas,
                pk=request.POST.get("linha_id"),
                situacao=S.VALIDA
            )

            campos = [
                "nome",
                "data_nascimento",
                "ra",
                "matricula",
                "serie",
                "celular",
                "email",
                "endereco",
                "bairro",
                "cidade",
                "cep",
                "resp_nome",
                "resp_email",
                "resp_celular",
                "resp_data_nascimento",
                "resp_cep",
                "resp_endereco",
                "resp_bairro",
            ]

            bruto = {
                campo: request.POST.get(campo, "").strip()
                for campo in campos
            }

            resultado, erros = validar_edicao(
                imp,
                linha,
                bruto
            )

            if erros:

                for erro in erros:
                    messages.error(request, erro)

                return redirect("importacao:previa", pk=imp.pk)

            linha.dados = resultado["dados"]
            linha.nome = resultado["dados"]["nome"]
            linha.ra = resultado["dados"]["ra"]
            linha.aviso = "; ".join(resultado["avisos"])

            linha.save(update_fields=[
                "dados",
                "nome",
                "ra",
                "aviso"
            ])

            messages.success(
                request,
                f"Dados de {linha.nome} atualizados na prévia."
            )

            return redirect("importacao:previa", pk=imp.pk)

        # CONFIRMAR IMPORTAÇÃO
        if acao == "confirmar":

            if imp.linhas.filter(situacao=S.VALIDA).exists():

                services.confirmar(imp, request.user)

                return redirect(
                    "importacao:resultado",
                    pk=imp.pk
                )

            messages.error(
                request,
                "Não existem alunos válidos para importar."
            )

            return redirect("importacao:previa", pk=imp.pk)

    # LISTA DE TODOS OS ALUNOS VÁLIDOS
    validas = list(
        imp.linhas.filter(situacao=S.VALIDA)
    )

    amostra = []

    for l in validas:

        dados = l.dados.copy()

        dados["idade"] = calcular_idade(
            dados.get("data_nascimento")
        )

        dados["idade_responsavel"] = calcular_idade(
            dados.get("resp_data_nascimento")
        )

        amostra.append({
            "id": l.pk,
            "numero": l.numero_linha,
            "acao": dados.get("_acao"),
            "dados": dados,
        })

    contexto = {
        "imp": imp,

        "a_criar": sum(
            1 for l in validas
            if l.dados.get("_acao") == "criar"
        ),

        "a_atualizar": sum(
            1 for l in validas
            if l.dados.get("_acao") == "atualizar"
        ),

        "rejeitadas": imp.linhas.filter(
            situacao=S.ERRO
        ),

        "com_aviso": imp.linhas.exclude(
            aviso=""
        ).exclude(
            situacao__in=[S.ERRO, S.EXCLUIDO]
        ),

        "excluidas": imp.linhas.filter(
            situacao=S.EXCLUIDO
        ).count(),

        "amostra": amostra,
    }

    return render(
        request,
        "importacao/previa.html",
        contexto
    )


@protegida
def resultado(request, pk):
    imp = get_object_or_404(Importacao, pk=pk)
    if imp.status == Importacao.Status.PREVIA:
        return redirect("importacao:previa", pk=imp.pk)
    contexto = {
        "imp": imp,
        "rejeitadas": imp.linhas.filter(situacao__in=[S.ERRO, S.REJEITADO]),
        "com_aviso": imp.linhas.exclude(aviso="").exclude(situacao__in=[S.ERRO, S.REJEITADO]),
    }
    return render(request, "importacao/resultado.html", contexto)


@protegida
def historico(request):
    return render(
        request, "importacao/historico.html",
        {"importacoes": Importacao.objects.select_related("usuario")[:50]},
    )


def _csv_response(nome_arquivo):
    resposta = HttpResponse(content_type="text/csv; charset=utf-8")
    resposta["Content-Disposition"] = f'attachment; filename="{nome_arquivo}"'
    resposta.write("\ufeff")  # BOM: o Excel abre com acentos corretos
    return resposta


@protegida
def erros_csv(request, pk):
    imp = get_object_or_404(Importacao, pk=pk)
    resposta = _csv_response(f"importacao_{imp.pk}_rejeitadas.csv")
    escritor = csv.writer(resposta, delimiter=";")
    escritor.writerow(["Linha no arquivo", "Aluno", "R.A.", "Situação", "Motivo"])
    for l in imp.linhas.filter(situacao__in=[S.ERRO, S.REJEITADO]):
        escritor.writerow([l.numero_linha, l.nome, l.ra, l.get_situacao_display(), l.motivo])
    return resposta


@protegida
def modelo_csv(request):
    resposta = _csv_response("modelo_importacao_alunos.csv")
    resposta.write(services.MODELO_CSV)
    return resposta