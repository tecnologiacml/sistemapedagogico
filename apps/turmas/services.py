from django.db import transaction

from .models import Matricula


class MatriculaInvalida(Exception):
    pass


@transaction.atomic
def matricular(aluno, turma, data_inicio):
    """Matricula o aluno na turma. Se já houver matrícula ativa, ela é encerrada (nunca apagada).

    Mesmo ano letivo -> "transferida"; ano diferente -> "concluida".
    Também mantém Aluno.unidade e Aluno.serie em dia, até esses campos saírem do aluno.
    """
    atual = aluno.matriculas.select_for_update().select_related("turma").filter(
        situacao=Matricula.Situacao.ATIVA
    ).first()
    if atual:
        if atual.turma_id == turma.pk:
            raise MatriculaInvalida("O aluno já está matriculado nesta turma.")
        if data_inicio < atual.data_inicio:
            raise MatriculaInvalida(
                f"A data não pode ser anterior ao início da matrícula atual ({atual.data_inicio:%d/%m/%Y})."
            )
        atual.data_fim = data_inicio
        atual.situacao = (
            Matricula.Situacao.TRANSFERIDA
            if atual.turma.ano_letivo_id == turma.ano_letivo_id
            else Matricula.Situacao.CONCLUIDA
        )
        atual.save(update_fields=["data_fim", "situacao"])

    nova = Matricula.objects.create(aluno=aluno, turma=turma, data_inicio=data_inicio)
    aluno.unidade = turma.unidade.nome
    aluno.serie = turma.serie.nome
    aluno.save(update_fields=["unidade", "serie"])
    return nova
