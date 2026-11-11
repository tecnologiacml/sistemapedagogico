from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView,
)

from .forms import AlunoForm
from .models import Aluno


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
        qs = Aluno.objects.select_related("responsavel").order_by("nome")
        self.q = self.request.GET.get("q", "").strip()
        if self.q:
            qs = qs.filter(
                Q(nome__icontains=self.q)
                | Q(ra__icontains=self.q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.q
        return ctx
    


class AlunoDetailView(LoginRequiredMixin, DetailView):
    model = Aluno


class AlunoCreateView(PodeEditarMixin, CreateView):
    model = Aluno
    form_class = AlunoForm
    success_url = reverse_lazy("alunos:lista")

    def form_valid(self, form):
        messages.success(self.request, "Aluno cadastrado com sucesso.")
        return super().form_valid(form)


class AlunoUpdateView(PodeEditarMixin, UpdateView):
    model = Aluno
    form_class = AlunoForm
    success_url = reverse_lazy("alunos:lista")

    def form_valid(self, form):
        messages.success(self.request, "Aluno atualizado com sucesso.")
        return super().form_valid(form)


class AlunoDeleteView(PodeExcluirMixin, DeleteView):
    model = Aluno
    success_url = reverse_lazy("alunos:lista")

    def form_valid(self, form):
        messages.success(self.request, "Aluno excluído.")
        return super().form_valid(form)