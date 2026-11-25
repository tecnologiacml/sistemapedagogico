import csv
import re
from datetime import date

from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.functional import cached_property
from django.views import View
from django.views.generic import CreateView, FormView, ListView, UpdateView

from apps.alunos.models import Aluno
from apps.usuarios.mixins import PerfilRequiredMixin

from . import importar
from .forms import ImportarMatriculasForm, MatriculaForm, TurmaForm
from .models import AnoLetivo, Matricula, Turma, Unidade
from .services import MatriculaInvalida, matricular, matricular_em_lote

# Por ora só o Administrador cadastra turmas (a secretaria ainda não é um perfil do sistema).
PERMISSAO_GERENCIAR = "pode_gerenciar_usuarios"


class TurmaListView(PerfilRequiredMixin, ListView):
    """Lista de turmas. A consulta respeita o ano letivo escolhido (padrão: o ano corrente)."""

    model = Turma
    paginate_by = 30

    def ano_escolhido(self):
        valor = self.request.GET.get("ano", "")
        if valor == "todos":
            return None
        if valor.isdigit():
            ano = AnoLetivo.objects.filter(pk=int(valor)).first()
            if ano:
                return ano
        hoje = timezone.localdate()
        return AnoLetivo.objects.filter(ano=hoje.year).first() or AnoLetivo.objects.first()

    def get_queryset(self):
        qs = super().get_queryset().select_related("unidade", "ano_letivo", "serie")
        ano = self.ano_escolhido()
        if ano:
            qs = qs.filter(ano_letivo=ano)
        unidade = self.request.GET.get("unidade", "")
        if unidade.isdigit():
            qs = qs.filter(unidade_id=int(unidade))
        q = self.request.GET.get("q", "").strip()
        # Cada palavra digitada precisa aparecer no nome da turma ou da série, em qualquer ordem.
        # "º" e "ª" são ignorados: "1 ano a" acha "1º ano A". Uma letra sozinha ("A", "B") é a
        # identificação da turma, então só vale como palavra inteira (senão o "a" de "ano" acharia tudo).
        for palavra in q.replace("º", "").replace("ª", "").split():
            if len(palavra) == 1:
                inteira = r"(^|\s)%s(\s|$)" % re.escape(palavra)
                qs = qs.filter(Q(nome__iregex=inteira) | Q(serie__nome__iregex=inteira))
            else:
                qs = qs.filter(
                    Q(nome__icontains=palavra) | Q(serie__nome__icontains=palavra)
                )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ano = self.ano_escolhido()
        unidade = self.request.GET.get("unidade", "")
        ctx.update({
            "anos": AnoLetivo.objects.all(),
            "unidades": Unidade.objects.all(),
            "ano_sel": "todos" if self.request.GET.get("ano") == "todos" else (ano.pk if ano else ""),
            "unidade_sel": int(unidade) if unidade.isdigit() else "",
            "q": self.request.GET.get("q", "").strip(),
            "pode_gerenciar": getattr(self.request.user, PERMISSAO_GERENCIAR, False),
        })
        return ctx


class TurmaCreateView(PerfilRequiredMixin, CreateView):
    model = Turma
    form_class = TurmaForm
    permissao = PERMISSAO_GERENCIAR
    success_url = reverse_lazy("turmas:lista")

    def form_valid(self, form):
        messages.success(self.request, "Turma cadastrada com sucesso.")
        return super().form_valid(form)


class TurmaUpdateView(PerfilRequiredMixin, UpdateView):
    model = Turma
    form_class = TurmaForm
    permissao = PERMISSAO_GERENCIAR
    success_url = reverse_lazy("turmas:lista")

    def form_valid(self, form):
        messages.success(self.request, "Turma atualizada com sucesso.")
        return super().form_valid(form)


class MatricularView(PerfilRequiredMixin, FormView):
    """Matricula o aluno em uma turma ou troca de turma, preservando o histórico (US-008)."""

    permissao = "pode_editar_alunos"
    form_class = MatriculaForm
    template_name = "turmas/matricula_form.html"

    @cached_property
    def aluno(self):
        # só é buscado depois da checagem de login e permissão
        return get_object_or_404(Aluno, pk=self.kwargs["aluno_pk"])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["aluno"] = self.aluno
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["aluno"] = self.aluno
        ctx["atual"] = ctx["form"].atual
        return ctx

    def form_valid(self, form):
        try:
            matricular(self.aluno, form.cleaned_data["turma"], form.cleaned_data["data_inicio"])
        except MatriculaInvalida as erro:
            form.add_error(None, str(erro))
            return self.form_invalid(form)
        messages.success(self.request, "Matrícula registrada. O histórico anterior foi preservado.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("alunos:detalhe", args=[self.aluno.pk])


SESSAO_IMPORTACAO = "importar_matriculas"


class ImportarMatriculasView(PerfilRequiredMixin, View):
    """Troca de turma em lote por planilha: envia, confere (prévia) e só então aplica."""

    permissao = "pode_editar_alunos"
    template_name = "turmas/importar_matriculas.html"

    def get(self, request):
        return render(request, self.template_name, {"form": ImportarMatriculasForm()})

    def post(self, request):
        if request.POST.get("confirmar"):
            return self.confirmar(request)
        form = ImportarMatriculasForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})
        try:
            linhas = importar.ler_planilha(form.cleaned_data["arquivo"].read())
        except importar.PlanilhaInvalida as erro:
            form.add_error("arquivo", str(erro))
            return render(request, self.template_name, {"form": form})
        previa = importar.validar(linhas)
        validas = [(r["aluno_id"], r["turma_id"]) for r in previa if r["status"] == importar.OK]
        request.session[SESSAO_IMPORTACAO] = {
            "pares": validas, "data": form.cleaned_data["data_inicio"].isoformat(),
        }
        ordem = {importar.ERRO: 0, importar.IGNORADO: 1, importar.OK: 2}
        contexto = {
            "form": ImportarMatriculasForm(initial={"data_inicio": form.cleaned_data["data_inicio"]}),
            "previa": sorted(previa, key=lambda r: (ordem[r["status"]], r["numero"])),
            "n_ok": len(validas),
            "n_ignorados": sum(r["status"] == importar.IGNORADO for r in previa),
            "n_erros": sum(r["status"] == importar.ERRO for r in previa),
            "data": form.cleaned_data["data_inicio"],
        }
        return render(request, self.template_name, contexto)

    def confirmar(self, request):
        dados = request.session.pop(SESSAO_IMPORTACAO, None)
        if not dados or not dados["pares"]:
            messages.error(request, "Não há importação para aplicar. Envie a planilha de novo.")
            return redirect("turmas:importar_matriculas")
        data = date.fromisoformat(dados["data"])
        alunos = Aluno.objects.in_bulk([a for a, _ in dados["pares"]])
        turmas = Turma.objects.select_related("unidade", "serie").in_bulk([t for _, t in dados["pares"]])
        pares = [(alunos[a], turmas[t]) for a, t in dados["pares"] if a in alunos and t in turmas]
        aplicadas, ignoradas = matricular_em_lote(pares, data)
        texto = f"{aplicadas} matrícula(s) registrada(s). O histórico anterior foi preservado."
        if ignoradas:
            texto += f" {ignoradas} ignorada(s) por já estarem na turma ou por data anterior."
        messages.success(request, texto)
        return redirect("turmas:lista")


class ExportarSemTurmaView(PerfilRequiredMixin, View):
    """Planilha com os alunos que ainda estão na turma provisória, para preencher a coluna "turma"."""

    permissao = "pode_editar_alunos"

    def get(self, request):
        ativas = Matricula.objects.filter(
            situacao=Matricula.Situacao.ATIVA, turma__nome__startswith=importar.PREFIXO_PROVISORIA
        ).select_related("aluno").order_by("aluno__nome")
        resposta = HttpResponse(content_type="text/csv; charset=utf-8")
        resposta["Content-Disposition"] = 'attachment; filename="alunos_sem_turma.csv"'
        resposta.write("\ufeff")  # para o Excel abrir os acentos certos
        escritor = csv.writer(resposta, delimiter=";")
        escritor.writerow(["ra", "nome", "unidade", "turma"])
        for m in ativas:
            escritor.writerow([m.aluno.ra or "", m.aluno.nome, m.aluno.unidade, ""])
        return resposta
