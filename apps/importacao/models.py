from django.conf import settings
from django.db import models

from apps.alunos.models import Aluno


class Importacao(models.Model):
    """Cada envio de CSV. Guarda os totais para servir de log."""

    class Status(models.TextChoices):
        PREVIA = "previa", "Prévia (nada foi gravado)"
        PROCESSANDO = "processando", "Processando"
        CONCLUIDA = "concluida", "Concluída"
        CANCELADA = "cancelada", "Cancelada"

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="importacoes_alunos"
    )
    arquivo_nome = models.CharField(max_length=255)
    unidade = models.CharField(max_length=20, choices=Aluno.Unidade.choices)
    atualizar_existentes = models.BooleanField(default=False)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PREVIA)
    criado_em = models.DateTimeField(auto_now_add=True)
    concluido_em = models.DateTimeField(null=True, blank=True)
    colunas_ignoradas = models.TextField(blank=True)
    # resultado da validação (prévia)
    total_linhas = models.PositiveIntegerField(default=0)
    total_validas = models.PositiveIntegerField(default=0)
    total_erros = models.PositiveIntegerField(default=0)
    # resultado da gravação
    qtd_criados = models.PositiveIntegerField(default=0)
    qtd_atualizados = models.PositiveIntegerField(default=0)
    qtd_rejeitados = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "importação de alunos"
        verbose_name_plural = "importações de alunos"
        permissions = [("importar_alunos", "Pode importar alunos por CSV")]

    def __str__(self):
        return f"{self.arquivo_nome} ({self.criado_em:%d/%m/%Y %H:%M})"


class ImportacaoLinha(models.Model):
    class Situacao(models.TextChoices):
        VALIDA = "valida", "Válida (aguardando confirmação)"
        ERRO = "erro", "Rejeitada na validação"
        CRIADO = "criado", "Cadastrado"
        ATUALIZADO = "atualizado", "Atualizado"
        REJEITADO = "rejeitado", "Rejeitado ao gravar"
        EXCLUIDO = "excluido", "Removido da prévia"

    importacao = models.ForeignKey(Importacao, on_delete=models.CASCADE, related_name="linhas")
    numero_linha = models.PositiveIntegerField()  # linha do arquivo (1 = cabeçalho)
    nome = models.CharField(max_length=255, blank=True)
    ra = models.CharField(max_length=50, blank=True)
    situacao = models.CharField(max_length=12, choices=Situacao.choices)
    motivo = models.TextField(blank=True)  # por que foi rejeitada
    aviso = models.TextField(blank=True)  # importada, mas com algo descartado
    # dados já limpos, só até a confirmação; é esvaziado ao concluir (minimização)
    dados = models.JSONField(default=dict, blank=True)
    aluno = models.ForeignKey("alunos.Aluno", null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["numero_linha"]
        indexes = [models.Index(fields=["importacao", "situacao"])]

    @property
    def acao(self):
        return {"criar": "Cadastrar", "atualizar": "Atualizar"}.get(self.dados.get("_acao"), "")