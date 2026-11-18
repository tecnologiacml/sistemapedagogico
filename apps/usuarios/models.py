from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    """Usuário do sistema, com um perfil de acesso.

    Só entra no sistema quem o administrador cadastrou. Alunos não são usuários: são cadastros.

    O perfil define o pacote base de funcionalidades. Além dele, o administrador pode liberar
    funcionalidades extras para um usuário específico (campo permissoes_extras).
    """

    class Perfil(models.TextChoices):
        ADMINISTRADOR = "administrador", "Administrador"
        COORDENACAO = "coordenacao", "Coordenação"
        GESTOR = "gestor", "Gestor pedagógico"
        ORIENTADOR = "orientador", "Orientador"

    # Funcionalidades que o administrador pode liberar além do perfil (chave = nome da propriedade pode_*).
    # "Gerenciar usuários" fica de fora de propósito: só o perfil Administrador tem.
    FUNCIONALIDADES = {
        "pode_editar_alunos": "Cadastrar e editar alunos",
        "pode_editar_encontros": "Cadastrar e editar encontros",
        "pode_excluir_alunos": "Excluir alunos",
    }

    # O que cada perfil já inclui por padrão.
    FUNCIONALIDADES_DO_PERFIL = {
        Perfil.ADMINISTRADOR: {
            "pode_editar_alunos", "pode_editar_encontros", "pode_excluir_alunos", "pode_gerenciar_usuarios",
        },
        Perfil.ORIENTADOR: {"pode_editar_alunos", "pode_editar_encontros"},
        Perfil.COORDENACAO: set(),
        Perfil.GESTOR: set(),
    }

    email = models.EmailField("e-mail", unique=True)
    perfil = models.CharField(
        max_length=20, choices=Perfil.choices, default=Perfil.ORIENTADOR
    )
    permissoes_extras = models.JSONField(
        "liberações extras", default=list, blank=True,
        help_text="Funcionalidades liberadas para este usuário além do que o perfil já inclui.",
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

    # ---- Permissões: perfil + liberações extras (conferidas no servidor em PerfilRequiredMixin) ----
    def tem_funcionalidade(self, chave):
        if chave in self.FUNCIONALIDADES_DO_PERFIL.get(self.perfil, set()):
            return True
        return chave in self.FUNCIONALIDADES and chave in (self.permissoes_extras or [])

    @property
    def pode_editar_alunos(self):
        """Administrador e orientador cadastram e editam. Os demais, só com liberação extra."""
        return self.tem_funcionalidade("pode_editar_alunos")

    @property
    def pode_editar_encontros(self):
        """Quem cadastra encontros: administrador e orientador, ou quem recebeu a liberação."""
        return self.tem_funcionalidade("pode_editar_encontros")

    @property
    def pode_excluir_alunos(self):
        return self.tem_funcionalidade("pode_excluir_alunos")

    @property
    def pode_gerenciar_usuarios(self):
        return self.perfil == self.Perfil.ADMINISTRADOR

    @property
    def nivel_acesso(self):
        """Texto curto para telas: o que este usuário pode fazer."""
        if self.perfil == self.Perfil.ADMINISTRADOR:
            return "Visualiza e edita tudo"
        base = "Visualiza e edita" if self.perfil == self.Perfil.ORIENTADOR else "Somente visualiza"
        extras = [c for c in (self.permissoes_extras or []) if c in self.FUNCIONALIDADES]
        if extras and base == "Somente visualiza":
            base = "Visualiza"
        return f"{base} (+{len(extras)} liberação extra)" if extras else base