import calendar
from datetime import date, timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.utils import timezone
from django.views.generic import TemplateView

from apps.alunos.models import Aluno
from apps.importacao.models import Importacao

MESES = [
    "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]
DIAS_SEMANA = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]


def _mes_da_url(texto, hoje):
    """Lê ?mes=AAAA-MM; qualquer valor inválido volta para o mês atual."""
    try:
        ano, mes = (int(p) for p in (texto or "").split("-"))
        return date(ano, mes, 1) if 1900 <= ano <= 2100 else hoje.replace(day=1)
    except (ValueError, TypeError):
        return hoje.replace(day=1)


def _deslocar_mes(primeiro_dia, delta):
    indice = primeiro_dia.year * 12 + (primeiro_dia.month - 1) + delta
    return date(indice // 12, indice % 12 + 1, 1)


def _rotulo_dia(dia, hoje):
    if dia == hoje:
        return "Hoje"
    if dia == hoje + timedelta(days=1):
        return "Amanhã"
    return f"{DIAS_SEMANA[dia.weekday()]}, {dia:%d/%m}"


class InicioView(LoginRequiredMixin, TemplateView):
    """Tela de entrada: boas-vindas, calendário, atividades recentes e aniversariantes da semana."""

    template_name = "inicio/inicio.html"

    def _calendario(self, hoje):
        primeiro = _mes_da_url(self.request.GET.get("mes"), hoje)
        com_aniversario = set(
            Aluno.objects.filter(data_nascimento__month=primeiro.month)
            .values_list("data_nascimento__day", flat=True)
        )
        semanas = []
        for semana in calendar.Calendar(firstweekday=0).monthdatescalendar(primeiro.year, primeiro.month):
            semanas.append([
                {
                    "dia": d.day,
                    "fora": d.month != primeiro.month,
                    "hoje": d == hoje,
                    "aniversario": d.month == primeiro.month and d.day in com_aniversario,
                }
                for d in semana
            ])
        anterior, seguinte = _deslocar_mes(primeiro, -1), _deslocar_mes(primeiro, 1)
        return {
            "titulo_mes": f"{MESES[primeiro.month]} {primeiro.year}",
            "mes_anterior": f"{anterior:%Y-%m}",
            "mes_seguinte": f"{seguinte:%Y-%m}",
            "semanas": semanas,
            "dias_semana": DIAS_SEMANA,
        }

    def _aniversariantes(self, hoje):
        """Alunos que fazem aniversário de hoje até daqui a 6 dias (sem foto, só nome e data)."""
        dias = [hoje + timedelta(days=i) for i in range(7)]
        filtro = Q()
        for d in dias:
            filtro |= Q(data_nascimento__month=d.month, data_nascimento__day=d.day)
        por_data = {(d.month, d.day): d for d in dias}

        lista = []
        for aluno in Aluno.objects.filter(filtro).order_by("nome"):
            dia = por_data[(aluno.data_nascimento.month, aluno.data_nascimento.day)]
            lista.append({
                "nome": aluno.nome,
                "rotulo": _rotulo_dia(dia, hoje),
                "idade": dia.year - aluno.data_nascimento.year,
                "ordem": dia,
            })
        lista.sort(key=lambda x: (x["ordem"], x["nome"]))
        return lista

    def _atividades(self):
        concluidas = (
            Importacao.objects.filter(status=Importacao.Status.CONCLUIDA)
            .select_related("usuario")
            .order_by("-concluido_em")[:5]
        )
        return [
            {
                "texto": f"Importação concluída: {i.qtd_criados} cadastrado(s), {i.qtd_atualizados} atualizado(s)",
                "quando": timezone.localtime(i.concluido_em) if i.concluido_em else None,
            }
            for i in concluidas
        ]

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        hoje = timezone.localdate()
        contexto["calendario"] = self._calendario(hoje)
        contexto["aniversariantes"] = self._aniversariantes(hoje)
        contexto["atividades"] = self._atividades()
        return contexto