"""Registro de auditoria das contas de usuário (US-003)."""

from .models import RegistroAuditoria, Usuario

CAMPOS = [
    ("first_name", "Nome"),
    ("last_name", "Sobrenome"),
    ("email", "E-mail"),
    ("perfil", "Perfil"),
    ("is_active", "Pode entrar no sistema"),
    ("is_staff", "Acesso ao Django Admin"),
    ("is_superuser", "Superusuário"),
    ("permissoes_extras", "Liberações extras"),
]
_BOOLEANOS = {"is_active", "is_staff", "is_superuser"}


def _valor(usuario, campo):
    v = getattr(usuario, campo)
    if campo == "perfil":
        return dict(Usuario.Perfil.choices).get(v, v)
    if campo in _BOOLEANOS:
        return "Sim" if v else "Não"
    if campo == "permissoes_extras":
        nomes = [Usuario.FUNCIONALIDADES[c] for c in (v or []) if c in Usuario.FUNCIONALIDADES]
        return ", ".join(nomes) or "nenhuma"
    return v or "—"


def snapshot(usuario):
    """Foto dos campos auditados, em texto legível."""
    return {campo: _valor(usuario, campo) for campo, _ in CAMPOS}


def diferencas(antes, depois):
    return [
        {"campo": rotulo, "antes": antes[campo], "depois": depois[campo]}
        for campo, rotulo in CAMPOS
        if antes[campo] != depois[campo]
    ]


def dados_iniciais(depois):
    return [{"campo": rotulo, "antes": "", "depois": depois[campo]} for campo, rotulo in CAMPOS]


def registrar(alvo, feito_por, acao, alteracoes=None):
    autor = feito_por if getattr(feito_por, "pk", None) else None
    return RegistroAuditoria.objects.create(
        alvo=alvo,
        alvo_username=alvo.username,
        feito_por=autor,
        feito_por_username=autor.username if autor else "",
        acao=acao,
        alteracoes=alteracoes or [],
    )
