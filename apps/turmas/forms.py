from django import forms

from django.utils import timezone

from .models import Matricula, Turma, Unidade


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


class MatriculaForm(forms.Form):
    turma = forms.ModelChoiceField(
        label="Turma", queryset=Turma.objects.none(), empty_label="Selecione a turma…"
    )
    data_inicio = forms.DateField(
        label="Data da matrícula",
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )

    def __init__(self, *args, aluno, **kwargs):
        super().__init__(*args, **kwargs)
        self.aluno = aluno
        self.atual = aluno.matriculas.select_related("turma").filter(
            situacao=Matricula.Situacao.ATIVA
        ).first()
        turmas = Turma.objects.filter(ativa=True).select_related("serie", "unidade", "ano_letivo")
        self.fields["turma"].queryset = turmas
        self.fields["turma"].label_from_instance = (
            lambda t: f"{t.ano_letivo} · {t.unidade} · {t.serie} · {t.nome}"
        )
        self.fields["data_inicio"].initial = timezone.localdate()
        self.fields["turma"].widget.attrs.setdefault("class", "form-select")
        self.fields["data_inicio"].widget.attrs.setdefault("class", "form-control")

    def clean_turma(self):
        turma = self.cleaned_data["turma"]
        if self.atual and self.atual.turma_id == turma.pk:
            raise forms.ValidationError("O aluno já está matriculado nesta turma.")
        return turma

    def clean_data_inicio(self):
        data = self.cleaned_data["data_inicio"]
        if self.atual and data < self.atual.data_inicio:
            raise forms.ValidationError(
                f"A data não pode ser anterior ao início da matrícula atual ({self.atual.data_inicio:%d/%m/%Y})."
            )
        return data
