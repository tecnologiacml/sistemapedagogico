from django import forms
from django.contrib.auth.forms import BaseUserCreationForm
from django.contrib.auth.password_validation import validate_password

from .models import Usuario

CAMPOS = ["first_name", "last_name", "username", "email", "perfil"]


def _estilizar(form):
    for campo in form.fields.values():
        css = "form-select" if isinstance(campo.widget, forms.Select) else "form-control"
        if isinstance(campo.widget, forms.CheckboxInput):
            css = "form-check-input"
        campo.widget.attrs.setdefault("class", css)


class UsuarioCriarForm(BaseUserCreationForm):
    """Cadastro feito pelo administrador, com senha inicial."""

    class Meta:
        model = Usuario
        fields = CAMPOS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True
        self.fields["username"].help_text = "Usado para entrar no sistema. Sem espaços."
        _estilizar(self)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if Usuario.objects.filter(email=email).exists():
            raise forms.ValidationError("Já existe um usuário com este e-mail.")
        return email


class UsuarioEditarForm(forms.ModelForm):
    nova_senha = forms.CharField(
        label="Nova senha (opcional)", required=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Deixe em branco para manter a senha atual.",
    )

    class Meta:
        model = Usuario
        fields = ["first_name", "last_name", "email", "perfil", "is_active"]
        labels = {"is_active": "Pode entrar no sistema (ativo)"}

    def __init__(self, *args, usuario_logado=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True
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
        if commit:
            usuario.save()
        return usuario
