import re

from django import forms
from django.core.exceptions import ValidationError

from .models import Aluno


class AlunoForm(forms.ModelForm):
    email = forms.EmailField(label="E-mail", required=False)
    celular = forms.CharField(
        label="Celular",
        required=False,
        max_length=11,
        widget=forms.TextInput(attrs={
            "type": "tel",
            "inputmode": "numeric",
            "placeholder": "(79) 99999-9999",
        }),
    )

    class Meta:
        model = Aluno
        fields = [
            "nome", "matricula", "ra", "serie", "unidade", "data_nascimento",
            "celular", "email", "endereco", "bairro", "cidade", "cep",
        ]
        widgets = {
            "data_nascimento": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def clean_nome(self):
        return " ".join(self.cleaned_data["nome"].split())

    def clean_celular(self):
        celular = self.cleaned_data.get("celular")
        if not celular:
            return celular
        digitos = re.sub(r"\D", "", celular)  # tira (), espaços e traços
        if len(digitos) not in (10, 11):
            raise ValidationError("Informe o celular com DDD (10 ou 11 dígitos).")
        return digitos

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:  
            self.fields["unidade"].initial = Aluno.Unidade.CENTRO
        for campo in self.fields.values():
            css = "form-select" if isinstance(campo.widget, forms.Select) else "form-control"
            campo.widget.attrs.setdefault("class", css)