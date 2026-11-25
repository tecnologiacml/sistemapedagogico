from django.db import transaction

from apps.alunos.models import Aluno

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


@transaction.atomic
def matricular_em_lote(pares, data_inicio):
    """Matricula vários alunos de uma vez: lista de (aluno, turma). Mesma regra de `matricular`.

    Devolve (aplicadas, ignoradas). Ignora quem já está na turma ou teria data anterior ao início
    da matrícula atual. Poucas consultas ao banco, para dar conta de centenas de alunos.
    """
    ativas = {
        m.aluno_id: m
        for m in Matricula.objects.select_for_update().select_related("turma").filter(
            aluno_id__in=[a.pk for a, _ in pares], situacao=Matricula.Situacao.ATIVA
        )
    }
    encerrar, novas, alunos, ignoradas = [], [], [], 0
    for aluno, turma in pares:
        atual = ativas.get(aluno.pk)
        if atual:
            if atual.turma_id == turma.pk or data_inicio < atual.data_inicio:
                ignoradas += 1
                continue
            atual.data_fim = data_inicio
            atual.situacao = (
                Matricula.Situacao.TRANSFERIDA
                if atual.turma.ano_letivo_id == turma.ano_letivo_id
                else Matricula.Situacao.CONCLUIDA
            )
            encerrar.append(atual)
        novas.append(Matricula(aluno=aluno, turma=turma, data_inicio=data_inicio))
        aluno.unidade = turma.unidade.nome
        aluno.serie = turma.serie.nome
        alunos.append(aluno)
    # as antigas saem de "ativa" antes de as novas entrarem (índice de matrícula ativa única)
    Matricula.objects.bulk_update(encerrar, ["data_fim", "situacao"])
    Matricula.objects.bulk_create(novas)
    Aluno.objects.bulk_update(alunos, ["unidade", "serie"])
    return len(novas), ignoradas
