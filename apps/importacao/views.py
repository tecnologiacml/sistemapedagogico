import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.alunos.models import Aluno
from datetime import date

from . import services
from .forms import UploadCSVForm
from .models import Importacao, ImportacaoLinha

PERMISSAO = "importacao.importar_alunos"
S = ImportacaoLinha.Situacao

# Campos que a tela de edição da prévia envia. Do responsável pedagógico guardamos só o nome.
CAMPOS_EDITAVEIS = [
    "nome", "data_nascimento", "ra", "cpf", "unidade", "serie",
    "celular", "email", "endereco", "bairro", "cidade", "cep",
    "resp_nome", "resp_email", "resp_celular", "resp_data_nascimento",
    "resp_cep", "resp_endereco", "resp_bairro",
    "ped_nome",
]


def protegida(view):
    return login_required(permission_required(PERMISSAO, raise_exception=True)(view))


def calcular_idade(data_nascimento):
    """Calcula a idade a partir da data de nascimento."""
    if not data_nascimento:
        return "—"
    try:
        if isinstance(data_nascimento, str):
            data_nascimento = date.fromisoformat(data_nascimento)
        hoje = timezone.localdate()
        idade = hoje.year - data_nascimento.year
        if (hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day):
            idade -= 1
        return idade if idade >= 0 else "—"
    except (ValueError, TypeError):
        return "—"


def atualizar_totais(imp):
    """Atualiza os totais da prévia após alterações."""
    imp.total_validas = imp.linhas.filter(situacao=S.VALIDA).count()
    imp.total_erros = imp.linhas.filter(situacao=S.ERRO).count()
    imp.save(update_fields=["total_validas", "total_erros"])


def alunos_novos_sem_unidade(imp):
    """Linhas válidas que vão CADASTRAR um aluno e ainda não têm unidade (informativo: unidade é opcional)."""
    return [
        l for l in imp.linhas.filter(situacao=S.VALIDA)
        if l.dados.get("_acao") == "criar" and not l.dados.get("unidade")
    ]


def validar_edicao(imp, linha, bruto):
    """Valida os dados editados antes de atualizar a prévia."""
    dados, erros, avisos = services.validar_campos(bruto)
    if erros:
        return None, erros

    aluno_id = linha.dados.get("_aluno_id")

    # R.A. já pertence a outro aluno?
    if dados["ra"]:
        qs = Aluno.objects.filter(ra=dados["ra"])
        if aluno_id:
            qs = qs.exclude(pk=aluno_id)
        if qs.exists():
            erros.append("Este R.A. já está cadastrado para outro aluno.")

    # CPF (opcional: validar_campos não o devolve, então vem do que já estava guardado)
    cpf = dados.get("cpf") or bruto.get("cpf", "")
    if cpf:
        qs = Aluno.objects.filter(cpf=cpf)
        if aluno_id:
            qs = qs.exclude(pk=aluno_id)
        if qs.exists():
            erros.append("Este CPF já está cadastrado para outro aluno.")

    # Duplicidade com as outras linhas válidas desta importação.
    outras = imp.linhas.filter(situacao=S.VALIDA).exclude(pk=linha.pk)
    for outra in outras:
        outro = outra.dados
        if dados["ra"] and dados["ra"] == outro.get("ra"):
            erros.append("Este R.A. já aparece em outro aluno desta importação.")
        if cpf and cpf == outro.get("cpf"):
            erros.append("Este CPF já aparece em outro aluno desta importação.")
        if (
            dados["nome"].strip().upper() == outro.get("nome", "").strip().upper()
            and dados["data_nascimento"] == outro.get("data_nascimento")
        ):
            erros.append("Já existe um aluno com o mesmo nome e data de nascimento nesta importação.")

    if erros:
        return None, list(dict.fromkeys(erros))

    # validar_campos já devolve "unidade" (opcional). Aqui voltam os campos internos
    # que ele não gera, para a edição não apagar o orientador nem a ação da linha.
    dados["responsavel_pedagogico_id"] = linha.dados.get("responsavel_pedagogico_id")
    dados["_acao"] = linha.dados.get("_acao", "criar")
    dados["_aluno_id"] = aluno_id
    return {"dados": dados, "avisos": avisos}, []


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
                atualizar_existentes=form.cleaned_data["atualizar_existentes"],
                unidade=form.cleaned_data.get("unidade", ""),  # opcional: padrão das linhas sem unidade
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

    if request.method == "POST":
        acao = request.POST.get("acao")

        # CANCELAR IMPORTAÇÃO
        if acao == "cancelar":
            services.cancelar(imp)
            messages.info(request, "Importação cancelada. Nenhum aluno foi cadastrado.")
            return redirect("importacao:importar")

        # DEFINIR A UNIDADE DOS ALUNOS NOVOS QUE ESTÃO SEM UNIDADE (opcional)
        if acao == "definir_unidade":
            unidade = request.POST.get("unidade", "")
            if unidade not in Aluno.Unidade.values:
                messages.error(request, "Escolha uma unidade válida.")
                return redirect("importacao:previa", pk=imp.pk)
            linhas = alunos_novos_sem_unidade(imp)
            for linha in linhas:
                linha.dados = {**linha.dados, "unidade": unidade}
                linha.save(update_fields=["dados"])
            messages.success(request, f"Unidade {unidade} aplicada a {len(linhas)} aluno(s) novo(s).")
            return redirect("importacao:previa", pk=imp.pk)

        # EXCLUIR ALUNO DA PRÉVIA
        if acao == "excluir":
            linha = get_object_or_404(imp.linhas, pk=request.POST.get("linha_id"), situacao=S.VALIDA)
            linha.situacao = S.EXCLUIDO
            linha.dados = {}
            linha.save(update_fields=["situacao", "dados"])
            atualizar_totais(imp)
            messages.success(request, f"Aluno {linha.nome} removido da importação.")
            return redirect("importacao:previa", pk=imp.pk)

        # EDITAR ALUNO
        if acao == "editar":
            linha = get_object_or_404(imp.linhas, pk=request.POST.get("linha_id"), situacao=S.VALIDA)

            # parte dos dados já guardados e troca só o que veio no formulário,
            # para não perder campos que a tela não mostra
            bruto = {k: v for k, v in linha.dados.items() if not k.startswith("_")}
            bruto.update({c: request.POST[c].strip() for c in CAMPOS_EDITAVEIS if c in request.POST})

            resultado, erros = validar_edicao(imp, linha, bruto)
            if erros:
                for erro in erros:
                    messages.error(request, erro)
                return redirect("importacao:previa", pk=imp.pk)

            linha.dados = resultado["dados"]
            linha.nome = resultado["dados"]["nome"]
            linha.ra = resultado["dados"]["ra"]
            linha.aviso = "; ".join(resultado["avisos"])
            linha.save(update_fields=["dados", "nome", "ra", "aviso"])
            messages.success(request, f"Dados de {linha.nome} atualizados na prévia.")
            return redirect("importacao:previa", pk=imp.pk)

        # CONFIRMAR IMPORTAÇÃO (unidade é opcional: não bloqueia mais)
        if acao == "confirmar":
            if not imp.linhas.filter(situacao=S.VALIDA).exists():
                messages.error(request, "Não existem alunos válidos para importar.")
                return redirect("importacao:previa", pk=imp.pk)

            services.confirmar(imp, request.user)
            return redirect("importacao:resultado", pk=imp.pk)

    # LISTA DE TODOS OS ALUNOS VÁLIDOS
    validas = list(imp.linhas.filter(situacao=S.VALIDA))

    amostra = []
    for l in validas:
        dados = l.dados.copy()
        dados["idade"] = calcular_idade(dados.get("data_nascimento"))
        dados["idade_responsavel"] = calcular_idade(dados.get("resp_data_nascimento"))
        amostra.append({
            "id": l.pk,
            "numero": l.numero_linha,
            "acao": dados.get("_acao"),
            "dados": dados,
        })

    contexto = {
        "imp": imp,
        "a_criar": sum(1 for l in validas if l.dados.get("_acao") == "criar"),
        "a_atualizar": sum(1 for l in validas if l.dados.get("_acao") == "atualizar"),
        "sem_unidade": sum(
            1 for l in validas if l.dados.get("_acao") == "criar" and not l.dados.get("unidade")
        ),
        "unidades": Aluno.Unidade.choices,
        "rejeitadas": imp.linhas.filter(situacao=S.ERRO),
        "com_aviso": imp.linhas.exclude(aviso="").exclude(situacao__in=[S.ERRO, S.EXCLUIDO]),
        "excluidas": imp.linhas.filter(situacao=S.EXCLUIDO).count(),
        "amostra": amostra,
    }
    return render(request, "importacao/previa.html", contexto)


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