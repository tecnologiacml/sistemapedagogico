from datetime import date

from django.db import models


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
    @property
    def celular_formatado(self):
     c = self.celular or ""
     if len(c) == 11:
        return f"({c[:2]}) {c[2:7]}-{c[7:]}"
     if len(c) == 10:
        return f"({c[:2]}) {c[2:6]}-{c[6:]}"
     return c

    class Unidade(models.TextChoices):
        CENTRO = "Centro", "Centro"
        CHIARA = "Chiara", "Chiara"

    nome = models.CharField(max_length=255)
    matricula = models.CharField(max_length=50, unique=True, null=True, blank=True)
    ra = models.CharField("Registro do aluno (RA)", max_length=50, null=True, blank=True)
    serie = models.CharField(max_length=50, null=True, blank=True)
    data_nascimento = models.DateField()
    celular = models.CharField(max_length=30, null=True, blank=True)
    email = models.CharField(max_length=255, null=True, blank=True)
    endereco = models.CharField(max_length=255, null=True, blank=True)
    bairro = models.CharField(max_length=255, null=True, blank=True)
    cidade = models.CharField(max_length=255, null=True, blank=True)
    cep = models.CharField(max_length=10, null=True, blank=True)
    unidade = models.CharField(max_length=20, choices=Unidade.choices)
    responsavel = models.ForeignKey(
        Responsavel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alunos",
    )

    class Meta:
        db_table = "alunos"
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    @property
    def idade(self):
        hoje = date.today()
        nasc = self.data_nascimento
        return hoje.year - nasc.year - ((hoje.month, hoje.day) < (nasc.month, nasc.day))