from django import forms
from django.core.exceptions import ValidationError

from .models import Aluno
from .validators import somente_digitos, validar_cpf


class AlunoForm(forms.ModelForm):
    # Aceita com ou sem máscara (até 14 caracteres); o clean guarda só dígitos.
    cpf = forms.CharField(label="CPF", max_length=14, help_text="Com ou sem pontuação.")

    class Meta:
        model = Aluno
        fields = ["nome", "cpf", "data_nascimento"]
        widgets = {
            "data_nascimento": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def clean_nome(self):
        return " ".join(self.cleaned_data["nome"].split())

    def clean_cpf(self):
        # Aceita "123.456.789-09" e guarda só os dígitos.
        cpf = somente_digitos(self.cleaned_data["cpf"])
        validar_cpf(cpf)
        qs = Aluno.objects.filter(cpf=cpf).exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("Já existe um aluno com este CPF.")
        return cpf

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            campo.widget.attrs.setdefault("class", "form-control")
