from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("alunos", "0002_alter_aluno_cpf_alter_aluno_data_nascimento"),
    ]

    operations = []  # ra e serie já são criados na 0003_responsavel_...