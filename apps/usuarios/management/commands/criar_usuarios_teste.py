"""Cria contas de teste para desenvolvimento (uma por perfil). Recusa rodar com DEBUG desligado.

  python manage.py criar_usuarios_teste
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.usuarios.models import Usuario

P = Usuario.Perfil
CONTAS = [  # username, perfil, nome, sobrenome
    ("admin", P.ADMINISTRADOR, "Admin", "Teste"),
    ("coord", P.COORDENACAO, "Coordenação", "Teste"),
    ("gestor", P.GESTOR, "Gestor", "Teste"),
    ("orientador", P.ORIENTADOR, "Orientador", "Teste"),
]


class Command(BaseCommand):
    help = "Cria as contas admin, coord, gestor e orientador (só para desenvolvimento)."

    def add_arguments(self, parser):
        parser.add_argument("--senha", default="Teste@123", help="Senha das contas de teste")

    def handle(self, *args, **opcoes):
        if not settings.DEBUG:
            raise CommandError("Este comando só roda com DEBUG=True (desenvolvimento).")
        for username, perfil, nome, sobrenome in CONTAS:
            usuario, criado = Usuario.objects.get_or_create(
                username=username,
                defaults={
                    "perfil": perfil, "first_name": nome, "last_name": sobrenome,
                    "email": f"{username}@teste.local",
                    "is_staff": perfil == P.ADMINISTRADOR, "is_superuser": perfil == P.ADMINISTRADOR,
                },
            )
            if criado:
                usuario.set_password(opcoes["senha"])
                usuario.save()
            self.stdout.write(f"{'criado ' if criado else 'já existe'}: {username} ({perfil})")
        self.stdout.write(self.style.WARNING("Contas de teste: nunca use estas senhas em produção."))
