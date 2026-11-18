import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("alunos", "0006_aluno_responsavel_pedagogico"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Encontro",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("numero", models.PositiveIntegerField(verbose_name="Nº do encontro")),
                ("data", models.DateField()),
                ("presente", models.BooleanField(default=True, verbose_name="Presença")),
                ("duracao", models.CharField(blank=True, choices=[("<20", "< 20"), ("20-25", "20–25"), ("25-30", "25–30"), (">30", "> 30")], max_length=5, verbose_name="Duração")),
                ("combinados_anteriores", models.CharField(blank=True, choices=[("primeiro", "1º Encontro"), ("realizou", "Realizou"), ("parcial", "Parcialmente"), ("nao_realizou", "Não realizou")], max_length=15, verbose_name="Combinados do encontro anterior")),
                ("temas", models.JSONField(blank=True, default=list, verbose_name="Temas tratados")),
                ("combinados_proximo", models.TextField(blank=True, verbose_name="Combinados para o próximo encontro")),
                ("habitos", models.CharField(blank=True, max_length=255, verbose_name="Hábitos / rotina")),
                ("hobbies", models.CharField(blank=True, max_length=255, verbose_name="Hobbies / interesses")),
                ("pontos_fortes", models.CharField(blank=True, max_length=255)),
                ("pontos_fracos", models.CharField(blank=True, max_length=255)),
                ("carreira_desejada", models.CharField(blank=True, max_length=255, verbose_name="Carreira desejada")),
                ("sabe_plurall", models.BooleanField(blank=True, null=True, verbose_name="Sabe utilizar o Plurall?")),
                ("encaminhamento", models.CharField(choices=[("nao", "Não"), ("psicologo", "Psicólogo(a)"), ("outro", "Outro")], default="nao", max_length=10)),
                ("motivo_encaminhamento", models.CharField(blank=True, max_length=255, verbose_name="Motivo do encaminhamento")),
                ("observacoes", models.TextField(blank=True, verbose_name="Observações")),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("aluno", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="encontros", to="alunos.aluno")),
                ("registrado_por", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Encontro",
                "verbose_name_plural": "Encontros",
                "ordering": ["-data", "-numero"],
            },
        ),
        migrations.AddConstraint(
            model_name="encontro",
            constraint=models.UniqueConstraint(fields=("aluno", "numero"), name="encontro_unico_por_aluno_numero"),
        ),
    ]
