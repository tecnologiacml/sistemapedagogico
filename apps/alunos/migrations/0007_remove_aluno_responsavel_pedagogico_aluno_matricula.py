from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("alunos", "0006_aluno_responsavel_pedagogico"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            # O que o Django registra internamente (igual ao original)
            state_operations=[
                migrations.RemoveField(
                    model_name="aluno",
                    name="responsavel_pedagogico",
                ),
                migrations.AddField(
                    model_name="aluno",
                    name="matricula",
                    field=models.CharField(blank=True, max_length=50, null=True, unique=True),
                ),
            ],
            # O que roda de fato no banco, tolerando estado parcial
            database_operations=[
                migrations.RunSQL(
                    sql=[
                        "ALTER TABLE alunos DROP COLUMN IF EXISTS responsavel_pedagogico_id CASCADE;",
                        "ALTER TABLE alunos ADD COLUMN IF NOT EXISTS matricula varchar(50) NULL;",
                        "CREATE UNIQUE INDEX IF NOT EXISTS alunos_matricula_uniq ON alunos (matricula);",
                    ],
                    reverse_sql=[
                        "DROP INDEX IF EXISTS alunos_matricula_uniq;",
                        "ALTER TABLE alunos DROP COLUMN IF EXISTS matricula;",
                    ],
                ),
            ],
        ),
    ]