from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    """Usuário do sistema, com um perfil de acesso.

    Só entra no sistema quem o administrador cadastrou. Alunos não são usuários: são cadastros.
    """

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

    # ---- Permissões por perfil (conferidas no servidor em PerfilRequiredMixin) ----
    @property
    def pode_editar_alunos(self):
        """Administrador e orientador cadastram e editam. Coordenação e gestor só visualizam."""
        return self.perfil in (self.Perfil.ADMINISTRADOR, self.Perfil.ORIENTADOR)

    @property
    def pode_excluir_alunos(self):
        return self.perfil == self.Perfil.ADMINISTRADOR

    @property
    def pode_gerenciar_usuarios(self):
        return self.perfil == self.Perfil.ADMINISTRADOR

    @property
    def nivel_acesso(self):
        """Texto curto para telas: o que este perfil pode fazer."""
        if self.perfil == self.Perfil.ADMINISTRADOR:
            return "Visualiza e edita tudo"
        if self.perfil == self.Perfil.ORIENTADOR:
            return "Visualiza e edita"
        return "Somente visualiza"
