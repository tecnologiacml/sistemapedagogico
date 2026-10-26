from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    """Usuário do sistema, com um perfil de acesso."""

    class Perfil(models.TextChoices):
        ADMINISTRADOR = "administrador", "Administrador"
        COORDENACAO = "coordenacao", "Coordenação"
        PROFESSOR = "professor", "Professor"

    perfil = models.CharField(
        max_length=20, choices=Perfil.choices, default=Perfil.PROFESSOR
    )

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"

    def save(self, *args, **kwargs):
        # Superusuário sempre é administrador.
        if self.is_superuser:
            self.perfil = self.Perfil.ADMINISTRADOR
        super().save(*args, **kwargs)

    # Regras de permissão usadas nas views e nos templates.
    @property
    def pode_editar_alunos(self):
        return self.perfil in (self.Perfil.ADMINISTRADOR, self.Perfil.COORDENACAO)

    @property
    def pode_excluir_alunos(self):
        return self.perfil == self.Perfil.ADMINISTRADOR
