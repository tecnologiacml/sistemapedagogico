from django.contrib import messages
from django.db.models import Count, Max, Q
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, ListView

from apps.alunos.models import Aluno
from apps.usuarios.mixins import PerfilRequiredMixin

from .forms import EncontroForm
from .models import Encontro


class EncontroListView(PerfilRequiredMixin, ListView):
    """Uma linha por aluno que já tem encontros."""

    model = Aluno
    template_name = "encontros/encontro_list.html"
    context_object_name = "alunos"
    paginate_by = 20

    def get_queryset(self):
        qs = (
            Aluno.objects
            .annotate(
                total=Count("encontros"),
                ultimo=Max("encontros__data"),
                ultimo_numero=Max("encontros__numero"),
            )
            .filter(total__gt=0)
            .order_by("nome")
        )
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(nome__icontains=q) | Q(ra__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "").strip()
        return ctx


class AlunoEncontrosView(PerfilRequiredMixin, DetailView):
    """Linha do tempo de encontros e combinados de um aluno (US-016 / US-023)."""

    model = Aluno
    template_name = "encontros/aluno_encontros.html"
    context_object_name = "aluno"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["encontros"] = (
            self.object.encontros
            .select_related("registrado_por")
            .order_by("-data", "-numero")  # mais recente primeiro
        )
        return ctx


class EncontroDetailView(PerfilRequiredMixin, DetailView):
    model = Encontro


class EncontroCreateView(PerfilRequiredMixin, CreateView):
    model = Encontro
    form_class = EncontroForm
    permissao = "pode_editar_encontros"

    def get_initial(self):
        initial = super().get_initial()
        initial["data"] = timezone.localdate()
        initial["presente"] = True
        # permite abrir "Novo encontro" já com o aluno escolhido: ?aluno=<id>
        aluno_id = self.request.GET.get("aluno", "")
        if aluno_id.isdigit():
            initial["aluno"] = aluno_id
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        aluno_id = ctx["form"]["aluno"].value()
        aluno = Aluno.objects.filter(pk=aluno_id).first() if str(aluno_id or "").isdigit() else None
        ctx["aluno_sel"] = aluno
        ctx["numero_previsto"] = Encontro.proximo_numero(aluno) if aluno else ""
        return ctx

    def form_valid(self, form):
        form.instance.registrado_por = self.request.user
        messages.success(self.request, "Encontro registrado com sucesso.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("encontros:aluno", args=[self.object.aluno_id])


class BuscarAlunoView(PerfilRequiredMixin, View):
    """JSON para o campo 'Buscar aluno ou RA' da tela de novo encontro."""

    permissao = "pode_editar_encontros"

    def get(self, request):
        q = request.GET.get("q", "").strip()
        if len(q) < 2:
            return JsonResponse({"resultados": []})
        alunos = Aluno.objects.filter(Q(nome__icontains=q) | Q(ra__icontains=q))[:8]
        resultados = []
        for a in alunos:
            ultimo = a.encontros.order_by("-numero").first()
            resultados.append({
                "id": a.pk,
                "ra": a.ra or "",
                "nome": a.nome,
                "serie": a.serie,
                "numero": Encontro.proximo_numero(a),
                "ultimo_combinado": ultimo.combinados_proximo if ultimo else "",
            })
        return JsonResponse({"resultados": resultados})