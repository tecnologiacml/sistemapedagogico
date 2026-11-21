from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView,
)

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
    model = Aluno
    paginate_by = 20

    def get_queryset(self):
        qs = Aluno.objects.select_related("responsavel", "responsavel_pedagogico").order_by("nome")
        self.q = self.request.GET.get("q", "").strip()

        if self.q:
            filtro = Q(nome__icontains=self.q) | Q(ra__icontains=self.q)

            digitos = somente_digitos(self.q)

            if digitos:
                filtro |= Q(cpf__contains=digitos)

            qs = qs.filter(filtro)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.q
        return ctx


class AlunoDetailView(LoginRequiredMixin, DetailView):
    model = Aluno
    queryset = Aluno.objects.select_related("responsavel", "responsavel_pedagogico")


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