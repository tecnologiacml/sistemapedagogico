from django import forms
from django.contrib.auth.forms import BaseUserCreationForm, PasswordChangeForm
from django.contrib.auth.password_validation import validate_password

from .models import Usuario

CAMPOS = ["first_name", "last_name", "username", "email", "perfil"]


def _estilizar(form):
    for campo in form.fields.values():
        css = "form-select" if isinstance(campo.widget, forms.Select) else "form-control"
        if isinstance(campo.widget, forms.CheckboxInput):
            css = "form-check-input"
        campo.widget.attrs.setdefault("class", css)


def _campo_extras():
    return forms.MultipleChoiceField(
        label="Liberar mais alguma funcionalidade para este usuário?",
        required=False,
        choices=list(Usuario.FUNCIONALIDADES.items()),
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        help_text="As funcionalidades que o perfil já inclui aparecem marcadas e bloqueadas. "
        "As demais só valem para este usuário.",
    )


def _base_por_perfil():
    """{perfil: [funcionalidades já incluídas]} — usado na tela para marcar/bloquear ao trocar o perfil."""
    return {
        perfil.value: sorted(c for c in Usuario.FUNCIONALIDADES_DO_PERFIL.get(perfil, set()) if c in Usuario.FUNCIONALIDADES)
        for perfil in Usuario.Perfil
    }


def _extras_efetivos(perfil, escolhidas):
    """Guarda só o que o perfil NÃO inclui (o resto seria redundante e sumiria ao trocar de perfil)."""
    base = Usuario.FUNCIONALIDADES_DO_PERFIL.get(perfil, set())
    escolhidas = set(escolhidas or [])
    return [c for c in Usuario.FUNCIONALIDADES if c in escolhidas and c not in base]


class UsuarioCriarForm(BaseUserCreationForm):
    """Cadastro feito pelo administrador, com senha inicial."""

    permissoes_extras = _campo_extras()

    class Meta:
        model = Usuario
        fields = CAMPOS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True
        self.fields["username"].help_text = "Usado para entrar no sistema. Sem espaços."
        self.base_por_perfil = _base_por_perfil()
        _estilizar(self)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if Usuario.objects.filter(email=email).exists():
            raise forms.ValidationError("Já existe um usuário com este e-mail.")
        return email

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.permissoes_extras = _extras_efetivos(usuario.perfil, self.cleaned_data.get("permissoes_extras"))
        usuario.precisa_trocar_senha = True  # a senha inicial é provisória: a pessoa cria a própria ao entrar
        if commit:
            usuario.save()
            if hasattr(self, "save_m2m"):
                self.save_m2m()
        return usuario


class UsuarioEditarForm(forms.ModelForm):
    nova_senha = forms.CharField(
        label="Nova senha (opcional)", required=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Deixe em branco para manter a senha atual. Se você definir uma senha, "
        "a pessoa será pedida a criar a própria no próximo acesso.",
    )
    permissoes_extras = _campo_extras()

    class Meta:
        model = Usuario
        fields = ["first_name", "last_name", "email", "perfil", "is_active"]
        labels = {"is_active": "Pode entrar no sistema (ativo)"}

    def __init__(self, *args, usuario_logado=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario_logado = usuario_logado
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True
        self.initial["permissoes_extras"] = list(self.instance.permissoes_extras or [])
        self.base_por_perfil = _base_por_perfil()
        _estilizar(self)
        # O administrador não pode tirar o próprio acesso nem mudar o próprio perfil (evita se trancar fora).
        if usuario_logado is not None and usuario_logado.pk == self.instance.pk:
            for nome in ("perfil", "is_active"):
                self.fields[nome].disabled = True
                self.fields[nome].help_text = "Você não pode alterar isto na sua própria conta."
        if self.instance.is_superuser:
            self.fields["perfil"].disabled = True
            self.fields["perfil"].help_text = "Superusuário é sempre Administrador."

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if Usuario.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Já existe um usuário com este e-mail.")
        return email

    def clean_nova_senha(self):
        senha = self.cleaned_data.get("nova_senha")
        if senha:
            validate_password(senha, self.instance)
        return senha

    def save(self, commit=True):
        usuario = super().save(commit=False)
        if self.cleaned_data.get("nova_senha"):
            usuario.set_password(self.cleaned_data["nova_senha"])
            # senha definida pelo administrador para OUTRA pessoa é provisória; na própria conta, não
            if self.usuario_logado is None or self.usuario_logado.pk != usuario.pk:
                usuario.precisa_trocar_senha = True
        usuario.permissoes_extras = _extras_efetivos(usuario.perfil, self.cleaned_data.get("permissoes_extras"))
        if commit:
            usuario.save()
        return usuario


class SenhaForm(PasswordChangeForm):
    """A própria pessoa troca a senha (pede a atual e confere a nova)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["old_password"].label = "Senha atual"
        self.fields["new_password1"].label = "Nova senha"
        self.fields["new_password2"].label = "Repita a nova senha"
        _estilizar(self)

    def clean_new_password1(self):
        nova = self.cleaned_data["new_password1"]
        if self.user.check_password(nova):
            raise forms.ValidationError("A nova senha precisa ser diferente da atual.")
        return nova