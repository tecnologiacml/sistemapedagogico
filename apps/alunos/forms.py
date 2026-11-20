import re

from django import forms
from django.core.exceptions import ValidationError

from .models import Aluno, Responsavel
from .validators import somente_digitos, validar_cpf


def limpar_celular(valor):
    """Tira (), espaços e traços e confere se tem DDD (10 ou 11 dígitos)."""
    if not valor:
        return valor
    digitos = re.sub(r"\D", "", valor)
    if len(digitos) not in (10, 11):
        raise ValidationError("Informe o celular com DDD (10 ou 11 dígitos).")
    return digitos


def _widget_celular():
    return forms.TextInput(attrs={
        "type": "tel",
        "inputmode": "numeric",
        "placeholder": "(79) 99999-9999",
    })


def _aplicar_css(form):
    for campo in form.fields.values():
        if isinstance(campo.widget, forms.RadioSelect):
            continue  # os botões de opção são desenhados no template
        css = "form-select" if isinstance(campo.widget, forms.Select) else "form-control"
        campo.widget.attrs.setdefault("class", css)


class AlunoForm(forms.ModelForm):
    email = forms.EmailField(label="E-mail", required=False)
    celular = forms.CharField(
        label="Celular", required=False, max_length=20, widget=_widget_celular()
    )

    # --- responsável: não é campo do Aluno, é uma escolha feita na própria tela ---
    responsavel_opcao = forms.ChoiceField(
        label="Responsável do aluno", choices=[], widget=forms.RadioSelect
    )
    responsavel_existente = forms.ModelChoiceField(
        label="Responsável já cadastrado",
        queryset=Responsavel.objects.order_by("nome"),
        required=False,
        empty_label="Selecione o responsável…",
    )

    class Meta:
        model = Aluno
        fields = [
            "nome",
            "ra",
            "serie",
            "cpf",
            "unidade",
            "responsavel_pedagogico",
            "data_nascimento",
            "celular",
            "email",
            "endereco",
            "bairro",
            "cidade",
            "cep",
        ]
        widgets = {
            "data_nascimento": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # o CPF pode ser digitado com pontos e traço; o sistema guarda só os números
        cpf = self.fields["cpf"]
        cpf.validators = [v for v in cpf.validators if v.__class__.__name__ != "MaxLengthValidator"]
        cpf.max_length = 14
        cpf.widget.attrs["maxlength"] = 14

        if not self.instance.pk:
            self.fields["unidade"].initial = Aluno.Unidade.CENTRO

        # Responsável pedagógico: só usuários ativos com perfil orientador
        # (limit_choices_to do model)
        pedagogico = self.fields["responsavel_pedagogico"]
        pedagogico.required = False
        pedagogico.empty_label = "Sem responsável pedagógico definido"
        pedagogico.label_from_instance = lambda u: u.get_full_name() or u.username
        # Se quem cadastra é um orientador, já vem escolhido ele mesmo
        if not self.instance.pk and user is not None and getattr(user, "perfil", "") == "orientador":
            pedagogico.initial = user.pk

        # Opções de responsável dependem de o aluno já ter ou não um
        if self.instance.pk and self.instance.responsavel_id:
            self.fields["responsavel_opcao"].choices = [
                ("manter", f"Manter o responsável atual ({self.instance.responsavel.nome})"),
                ("existente", "Trocar por um responsável já cadastrado"),
                ("novo", "Cadastrar um novo responsável agora"),
                ("nenhum", "Remover o vínculo (ficar sem responsável)"),
            ]
            self.fields["responsavel_opcao"].initial = "manter"
        else:
            self.fields["responsavel_opcao"].choices = [
                ("nenhum", "Cadastrar o responsável depois"),
                ("existente", "Escolher um responsável já cadastrado"),
                ("novo", "Cadastrar um novo responsável agora"),
            ]
            self.fields["responsavel_opcao"].initial = "nenhum"

        _aplicar_css(self)

    def clean_cpf(self):
        cpf = self.cleaned_data.get("cpf")
        if not cpf:
            return None
        validar_cpf(cpf)  # "CPF inválido." se os dígitos não conferem
        digitos = somente_digitos(cpf)
        if Aluno.objects.filter(cpf=digitos).exclude(pk=self.instance.pk).exists():
            raise ValidationError("Já existe um aluno com este CPF.")
        return digitos

    def clean_nome(self):
        return " ".join(self.cleaned_data["nome"].split())

    def clean_celular(self):
        return limpar_celular(self.cleaned_data.get("celular"))

    def clean(self):
        dados = super().clean()
        if dados.get("responsavel_opcao") == "existente" and not dados.get("responsavel_existente"):
            self.add_error("responsavel_existente", "Escolha o responsável na lista.")
        return dados


class ResponsavelForm(forms.ModelForm):
    email = forms.EmailField(label="E-mail", required=False)
    celular = forms.CharField(
        label="Celular", required=False, max_length=20, widget=_widget_celular()
    )

    class Meta:
        model = Responsavel
        fields = ["nome", "email", "celular", "data_nascimento", "cep", "endereco", "bairro"]
        widgets = {
            "data_nascimento": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Esta parte da tela fica escondida quando não é usada; sem isso o navegador
        # bloquearia o envio por causa do "nome" obrigatório oculto.
        self.use_required_attribute = False
        _aplicar_css(self)

    def clean_nome(self):
        return " ".join(self.cleaned_data["nome"].split())

    def clean_celular(self):
        return limpar_celular(self.cleaned_data.get("celular"))