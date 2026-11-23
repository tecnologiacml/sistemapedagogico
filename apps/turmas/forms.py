from django import forms

from .models import Turma, Unidade


class TurmaForm(forms.ModelForm):
    class Meta:
        model = Turma
        fields = ["nome", "serie", "unidade", "ano_letivo", "ativa"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["unidade"].queryset = Unidade.objects.filter(ativa=True)
        for nome, campo in self.fields.items():
            if isinstance(campo.widget, forms.CheckboxInput):
                css = "form-check-input"
            elif isinstance(campo.widget, forms.Select):
                css = "form-select"
            else:
                css = "form-control"
            campo.widget.attrs.setdefault("class", css)

    def clean_nome(self):
        return " ".join(self.cleaned_data["nome"].split())
