from django.conf import settings
from django.db import models

from apps.alunos.models import Aluno

TEMAS = [
    "Atenção/distração",
    "Estudos/aprendizagem",
    "Rotina/organização",
    "Planejamento de estudos",
    "Carreira",
    "Bem-estar",
]


class Encontro(models.Model):
    """Registro de um encontro de orientação com um aluno (aba 'Registro Geral' da planilha)."""

    class Duracao(models.TextChoices):
        MENOS_20 = "<20", "< 20"
        DE_20_A_25 = "20-25", "20–25"
        DE_25_A_30 = "25-30", "25–30"
        MAIS_30 = ">30", "> 30"

    class Combinados(models.TextChoices):
        PRIMEIRO = "primeiro", "1º Encontro"
        REALIZOU = "realizou", "Realizou"
        PARCIAL = "parcial", "Parcialmente"
        NAO_REALIZOU = "nao_realizou", "Não realizou"

    class Encaminhamento(models.TextChoices):
        NAO = "nao", "Não"
        PSICOLOGO = "psicologo", "Psicólogo(a)"
        OUTRO = "outro", "Outro"

    aluno = models.ForeignKey(Aluno, on_delete=models.PROTECT, related_name="encontros")
    numero = models.PositiveIntegerField("Nº do encontro")
    data = models.DateField()
    presente = models.BooleanField("Presença", default=True)
    duracao = models.CharField("Duração", max_length=5, choices=Duracao.choices, blank=True)

    combinados_anteriores = models.CharField(
        "Combinados do encontro anterior", max_length=15, choices=Combinados.choices, blank=True
    )
    temas = models.JSONField("Temas tratados", default=list, blank=True)
    combinados_proximo = models.TextField("Combinados para o próximo encontro", blank=True)

    habitos = models.CharField("Hábitos / rotina", max_length=255, blank=True)
    hobbies = models.CharField("Hobbies / interesses", max_length=255, blank=True)
    pontos_fortes = models.CharField(max_length=255, blank=True)
    pontos_fracos = models.CharField(max_length=255, blank=True)
    carreira_desejada = models.CharField("Carreira desejada", max_length=255, blank=True)
    sabe_plurall = models.BooleanField("Sabe utilizar o Plurall?", null=True, blank=True)

    encaminhamento = models.CharField(
        max_length=10, choices=Encaminhamento.choices, default=Encaminhamento.NAO
    )
    motivo_encaminhamento = models.CharField("Motivo do encaminhamento", max_length=255, blank=True)
    observacoes = models.TextField("Observações", blank=True)

    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Encontro"
        verbose_name_plural = "Encontros"
        ordering = ["-data", "-numero"]
        constraints = [
            models.UniqueConstraint(fields=["aluno", "numero"], name="encontro_unico_por_aluno_numero"),
        ]

    def __str__(self):
        return f"{self.aluno} · encontro {self.numero}"

    @staticmethod
    def proximo_numero(aluno):
        ultimo = aluno.encontros.aggregate(m=models.Max("numero"))["m"] or 0
        return ultimo + 1
