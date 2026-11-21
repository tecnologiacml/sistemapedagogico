from datetime import date

from django.conf import settings
from django.db import models

from .validators import validar_cpf


class Responsavel(models.Model):
    nome = models.CharField(max_length=255)
    email = models.CharField(max_length=255, null=True, blank=True)
    celular = models.CharField(max_length=30, null=True, blank=True)
    data_nascimento = models.DateField(null=True, blank=True)
    endereco = models.CharField(max_length=255, null=True, blank=True)
    bairro = models.CharField(max_length=255, null=True, blank=True)
    cep = models.CharField(max_length=10, null=True, blank=True)

    class Meta:
        db_table = "responsaveis"

    def __str__(self):
        return self.nome


class Aluno(models.Model):

    class Unidade(models.TextChoices):
        CENTRO = "Centro", "Centro"
        CHIARA = "Chiara", "Chiara"

    nome = models.CharField(max_length=255)
    ra = models.CharField(
        "Registro do aluno (RA)",
        max_length=50,
        unique=True,
        null=True,
        blank=True,
    )
    serie = models.CharField(max_length=50, null=True, blank=True)

    cpf = models.CharField(
        "CPF",
        max_length=11,
        unique=True,
        null=True,
        blank=True,
        validators=[validar_cpf],
        help_text="Somente números.",
    )

    data_nascimento = models.DateField()
    celular = models.CharField(max_length=30, null=True, blank=True)
    email = models.CharField(max_length=255, null=True, blank=True)
    endereco = models.CharField(max_length=255, null=True, blank=True)
    bairro = models.CharField(max_length=255, null=True, blank=True)
    cidade = models.CharField(max_length=255, null=True, blank=True)
    cep = models.CharField(max_length=10, null=True, blank=True)

    unidade = models.CharField(
        max_length=20,
        choices=Unidade.choices
    )

    # Responsável da família: pai, mãe, avós ou outro
    responsavel = models.ForeignKey(
        Responsavel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alunos"
    )

    # Responsável pedagógico = o orientador do aluno: usuário do sistema com perfil
    # "orientador". Não confundir com `responsavel` acima (pai, mãe, avós...).
    responsavel_pedagogico = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Responsável pedagógico",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alunos_pedagogico",
        limit_choices_to={"perfil": "orientador", "is_active": True},
    )

    class Meta:
        db_table = "alunos"
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    @property
    def celular_formatado(self):
        c = self.celular or ""

        if len(c) == 11:
            return f"({c[:2]}) {c[2:7]}-{c[7:]}"

        if len(c) == 10:
            return f"({c[:2]}) {c[2:6]}-{c[6:]}"

        return c

    @property
    def idade(self):
        hoje = date.today()
        nasc = self.data_nascimento

        return hoje.year - nasc.year - (
            (hoje.month, hoje.day) < (nasc.month, nasc.day)
        )