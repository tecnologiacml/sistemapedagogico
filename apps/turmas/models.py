from django.db import models
from django.db.models import F, Q
from django.utils import timezone


class Unidade(models.Model):
    """Unidade do colégio (Centro, Chiara...). Tabela própria para novas unidades entrarem sem mudar o código (RN-16)."""

    nome = models.CharField(max_length=100, unique=True)
    ativa = models.BooleanField(default=True)

    class Meta:
        db_table = "unidades"
        ordering = ["nome"]
        verbose_name = "Unidade"
        verbose_name_plural = "Unidades"

    def __str__(self):
        return self.nome


class AnoLetivo(models.Model):
    ano = models.PositiveIntegerField(unique=True)
    inicio = models.DateField(null=True, blank=True)
    fim = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "anos_letivos"
        ordering = ["-ano"]
        verbose_name = "Ano letivo"
        verbose_name_plural = "Anos letivos"

    def __str__(self):
        return str(self.ano)


class Serie(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "series"
        ordering = ["ordem", "nome"]
        verbose_name = "Série"
        verbose_name_plural = "Séries"

    def __str__(self):
        return self.nome


class Turma(models.Model):
    """Turma de uma série, em uma unidade, em um ano letivo. Anos diferentes são turmas diferentes."""

    nome = models.CharField(max_length=100)
    unidade = models.ForeignKey(Unidade, on_delete=models.PROTECT, related_name="turmas")
    ano_letivo = models.ForeignKey(AnoLetivo, on_delete=models.PROTECT, related_name="turmas")
    serie = models.ForeignKey(Serie, on_delete=models.PROTECT, related_name="turmas")
    ativa = models.BooleanField(default=True)

    class Meta:
        db_table = "turmas"
        ordering = ["-ano_letivo__ano", "unidade__nome", "serie__ordem", "nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["unidade", "ano_letivo", "nome"],
                name="turma_unica_por_unidade_ano_nome",
                violation_error_message="Já existe uma turma com este nome nesta unidade e neste ano letivo.",
            )
        ]

    def __str__(self):
        return f"{self.nome} · {self.ano_letivo}"


class Matricula(models.Model):
    """Vínculo do estudante com uma turma (e, por ela, unidade, série e ano letivo).

    Cada ano letivo gera uma matrícula nova. As anteriores nunca são apagadas nem
    sobrescritas: só são encerradas (data_fim e situação). Ver US-008 e RN-02.
    """

    class Situacao(models.TextChoices):
        ATIVA = "ativa", "Ativa"
        TRANSFERIDA = "transferida", "Transferida de turma"
        CONCLUIDA = "concluida", "Concluída"
        CANCELADA = "cancelada", "Cancelada"

    aluno = models.ForeignKey("alunos.Aluno", on_delete=models.CASCADE, related_name="matriculas")
    turma = models.ForeignKey(Turma, on_delete=models.PROTECT, related_name="matriculas")
    data_inicio = models.DateField(default=timezone.localdate)
    data_fim = models.DateField(null=True, blank=True)
    situacao = models.CharField(max_length=20, choices=Situacao.choices, default=Situacao.ATIVA)

    class Meta:
        db_table = "matriculas"
        ordering = ["-data_inicio", "-id"]
        verbose_name = "Matrícula"
        verbose_name_plural = "Matrículas"
        constraints = [
            models.UniqueConstraint(
                fields=["aluno"],
                condition=Q(situacao="ativa"),
                name="matricula_ativa_unica_por_aluno",
            ),
            models.CheckConstraint(
                condition=Q(data_fim__isnull=True) | Q(data_fim__gte=F("data_inicio")),
                name="matricula_fim_depois_do_inicio",
            ),
        ]

    def __str__(self):
        return f"{self.aluno} · {self.turma}"
