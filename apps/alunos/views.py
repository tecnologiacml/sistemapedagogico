from django.contrib import messages
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.usuarios.mixins import PerfilRequiredMixin

from .forms import AlunoForm
from .models import Aluno
from .validators import somente_digitos


class AlunoListView(PerfilRequiredMixin, ListView):
    model = Aluno
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q:
            filtro = Q(nome__icontains=q)
            digitos = somente_digitos(q)
            if digitos:
                filtro |= Q(cpf__contains=digitos)
            qs = qs.filter(filtro)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "").strip()
        return ctx


class AlunoDetailView(PerfilRequiredMixin, DetailView):
    model = Aluno


class AlunoCreateView(PerfilRequiredMixin, CreateView):
    model = Aluno
    form_class = AlunoForm
    permissao = "pode_editar_alunos"
    success_url = reverse_lazy("alunos:lista")

    def form_valid(self, form):
        messages.success(self.request, "Aluno cadastrado com sucesso.")
        return super().form_valid(form)


class AlunoUpdateView(PerfilRequiredMixin, UpdateView):
    model = Aluno
    form_class = AlunoForm
    permissao = "pode_editar_alunos"
    success_url = reverse_lazy("alunos:lista")

    def form_valid(self, form):
        messages.success(self.request, "Aluno atualizado com sucesso.")
        return super().form_valid(form)


class AlunoDeleteView(PerfilRequiredMixin, DeleteView):
    model = Aluno
    permissao = "pode_excluir_alunos"
    success_url = reverse_lazy("alunos:lista")

    def form_valid(self, form):
        messages.success(self.request, "Aluno excluído.")
        return super().form_valid(form)
