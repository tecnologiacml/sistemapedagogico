from django.db import models

from .validators import validar_cpf


class Aluno(models.Model):
    nome = models.CharField(max_length=150)
    cpf = models.CharField(
        "CPF", max_length=11, unique=True, validators=[validar_cpf],
        help_text="Somente números.",
    )
    data_nascimento = models.DateField("Data de nascimento")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Aluno"
        verbose_name_plural = "Alunos"
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    @property
    def cpf_formatado(self):
        c = self.cpf
        return f"{c[:3]}.{c[3:6]}.{c[6:9]}-{c[9:]}" if len(c) == 11 else c
