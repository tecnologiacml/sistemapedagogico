import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("alunos", "0005_aluno_cpf_alter_aluno_ra_alter_aluno_serie"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="aluno",
            name="responsavel_pedagogico",
            field=models.ForeignKey(
                blank=True,
                null=True,
                limit_choices_to={"perfil": "orientador", "is_active": True},
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="alunos_pedagogico",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Responsável pedagógico",
            ),
        ),
    ]
