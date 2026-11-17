from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("alunos", "0002_alter_aluno_cpf_alter_aluno_data_nascimento"),
    ]

    operations = [
        migrations.AddField(
            model_name="aluno",
            name="ra",
            field=models.CharField(blank=True, max_length=20, null=True, unique=True, verbose_name="RA"),
        ),
        migrations.AddField(
            model_name="aluno",
            name="serie",
            field=models.CharField(blank=True, max_length=30, verbose_name="Série"),
        ),
    ]
