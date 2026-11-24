from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.functional import cached_property
from django.views.generic import CreateView, FormView, ListView, UpdateView

from apps.alunos.models import Aluno
from apps.usuarios.mixins import PerfilRequiredMixin

from .forms import MatriculaForm, TurmaForm
from .services import MatriculaInvalida, matricular
from .models import AnoLetivo, Turma, Unidade

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
        # Cada palavra digitada precisa aparecer no nome da turma ou da série,
        # em qualquer ordem. "º" e "ª" são ignorados: "1 ano a" acha "1º ano A".
        for palavra in q.replace("º", "").replace("ª", "").split():
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
