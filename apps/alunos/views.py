from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.db.models import Prefetch, Q
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView,
)

from apps.turmas.models import AnoLetivo, Matricula, Serie, Turma, Unidade

from .forms import AlunoForm, ResponsavelForm
from .models import Aluno
from .validators import somente_digitos


class PodeEditarMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.pode_editar_alunos


class PodeExcluirMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.pode_excluir_alunos


class AlunoListView(LoginRequiredMixin, ListView):
    """Lista de alunos com busca (nome, R.A., CPF) e filtros pela matrícula ATUAL: ano, unidade, série e turma."""

    model = Aluno
    paginate_by = 20

    def _inteiro(self, nome):
        valor = self.request.GET.get(nome, "")
        return int(valor) if valor.isdigit() else None

    def get_queryset(self):
        atual = Prefetch(
            "matriculas",
            queryset=Matricula.objects.filter(situacao=Matricula.Situacao.ATIVA).select_related(
                "turma__serie", "turma__unidade", "turma__ano_letivo"
            ),
            to_attr="matricula_atual",
        )
        qs = (
            Aluno.objects.select_related("responsavel", "responsavel_pedagogico")
            .prefetch_related(atual)
            .order_by("nome")
        )

        # Busca: cada palavra precisa aparecer no nome, no R.A. ou (se tiver números) no CPF.
        # Assim "silva maria" acha "Maria Silva", e dois homônimos aparecem separados na lista.
        self.q = self.request.GET.get("q", "").strip()
        for palavra in self.q.split():
            filtro = Q(nome__icontains=palavra) | Q(ra__icontains=palavra)
            digitos = somente_digitos(palavra)
            if digitos:
                filtro |= Q(cpf__contains=digitos)
            qs = qs.filter(filtro)

        # Filtros: valem para a matrícula ativa do aluno (todos na mesma matrícula).
        self.filtros = {
            "ano": self._inteiro("ano"),
            "unidade": self._inteiro("unidade"),
            "serie": self._inteiro("serie"),
            "turma": self._inteiro("turma"),
        }
        condicoes = {}
        if self.filtros["ano"]:
            condicoes["matriculas__turma__ano_letivo_id"] = self.filtros["ano"]
        if self.filtros["unidade"]:
            condicoes["matriculas__turma__unidade_id"] = self.filtros["unidade"]
        if self.filtros["serie"]:
            condicoes["matriculas__turma__serie_id"] = self.filtros["serie"]
        if self.filtros["turma"]:
            condicoes["matriculas__turma_id"] = self.filtros["turma"]
        if condicoes:
            qs = qs.filter(matriculas__situacao=Matricula.Situacao.ATIVA, **condicoes)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.q
        ctx.update({f"{nome}_sel": valor or "" for nome, valor in self.filtros.items()})
        ctx["filtros_ativos"] = bool(self.q) or any(self.filtros.values())
        ctx["anos"] = AnoLetivo.objects.all()
        ctx["unidades"] = Unidade.objects.filter(ativa=True)
        ctx["series"] = Serie.objects.all()
        ctx["turmas"] = Turma.objects.filter(ativa=True).select_related("unidade", "ano_letivo")
        return ctx


class AlunoDetailView(LoginRequiredMixin, DetailView):
    model = Aluno
    queryset = Aluno.objects.select_related("responsavel", "responsavel_pedagogico").prefetch_related(
        "matriculas__turma__serie", "matriculas__turma__unidade", "matriculas__turma__ano_letivo"
    )


class AlunoSalvarMixin(PodeEditarMixin):
    """Cuida do formulário do aluno + (opcionalmente) do formulário do responsável."""

    form_class = AlunoForm
    success_url = reverse_lazy("alunos:lista")
    mensagem_sucesso = ""

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.setdefault("resp_form", ResponsavelForm(prefix="resp"))
        return contexto

    def post(self, request, *args, **kwargs):
        self.object = self.get_object() if "pk" in self.kwargs else None
        form = self.get_form()
        cadastrar_novo = request.POST.get("responsavel_opcao") == "novo"
        resp_form = ResponsavelForm(request.POST, prefix="resp") if cadastrar_novo else ResponsavelForm(prefix="resp")

        aluno_ok = form.is_valid()
        resp_ok = resp_form.is_valid() if cadastrar_novo else True

        if aluno_ok and resp_ok:
            return self._salvar(form, resp_form if cadastrar_novo else None)
        return self.render_to_response(self.get_context_data(form=form, resp_form=resp_form))

    @transaction.atomic
    def _salvar(self, form, resp_form):
        opcao = form.cleaned_data["responsavel_opcao"]
        aluno = form.save(commit=False)

        if opcao == "novo":
            aluno.responsavel = resp_form.save()
        elif opcao == "existente":
            aluno.responsavel = form.cleaned_data["responsavel_existente"]
        elif opcao == "nenhum":
            aluno.responsavel = None
        # "manter": não mexe no responsável atual

        aluno.save()
        self.object = aluno
        messages.success(self.request, self.mensagem_sucesso)
        return HttpResponseRedirect(self.get_success_url())


class AlunoCreateView(AlunoSalvarMixin, CreateView):
    model = Aluno
    mensagem_sucesso = "Aluno cadastrado com sucesso."


class AlunoUpdateView(AlunoSalvarMixin, UpdateView):
    model = Aluno
    mensagem_sucesso = "Aluno atualizado com sucesso."


class AlunoDeleteView(PodeExcluirMixin, DeleteView):
    model = Aluno
    success_url = reverse_lazy("alunos:lista")

    def form_valid(self, form):
        messages.success(self.request, "Aluno excluído.")
        return super().form_valid(form)