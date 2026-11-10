from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    """Usuário do sistema, com um perfil de acesso."""

    class Perfil(models.TextChoices):
        ADMINISTRADOR = "administrador", "Administrador"
        COORDENACAO = "coordenacao", "Coordenação"
        GESTOR = "gestor", "Gestor pedagógico"
        ORIENTADOR = "orientador", "Orientador"

    email = models.EmailField("e-mail", unique=True)
    perfil = models.CharField(
        max_length=20, choices=Perfil.choices, default=Perfil.ORIENTADOR
    )

    class Meta:
        db_table = "usuarios"
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        if self.is_superuser:
            self.perfil = self.Perfil.ADMINISTRADOR
        super().save(*args, **kwargs)