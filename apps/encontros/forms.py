from django import forms

from apps.alunos.models import Aluno

from .models import TEMAS, Encontro


class EncontroForm(forms.ModelForm):
    temas = forms.MultipleChoiceField(
        label="Temas tratados",
        choices=[(t, t) for t in TEMAS],
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    sabe_plurall = forms.TypedChoiceField(
        label="Sabe utilizar o Plurall?",
        choices=[("", "Não informado"), ("1", "Sim"), ("0", "Não")],
        coerce=lambda v: v == "1",
        empty_value=None,
        required=False,
        widget=forms.RadioSelect,
    )

    class Meta:
        model = Encontro
        fields = [
            "aluno", "data", "presente", "duracao", "combinados_anteriores", "temas",
            "combinados_proximo", "habitos", "hobbies", "pontos_fortes", "pontos_fracos",
            "carreira_desejada", "sabe_plurall", "encaminhamento", "motivo_encaminhamento",
            "observacoes",
        ]
        widgets = {
            "aluno": forms.HiddenInput,
            "data": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "presente": forms.RadioSelect(choices=[(True, "Sim"), (False, "Não")]),
            "duracao": forms.RadioSelect,
            "combinados_anteriores": forms.RadioSelect,
            "combinados_proximo": forms.Textarea(attrs={"rows": 3, "placeholder": "Sugestões de combinados"}),
            "habitos": forms.TextInput(attrs={"placeholder": "Ex.: academia, estudos"}),
            "hobbies": forms.TextInput(attrs={"placeholder": "Ex.: música, jogos"}),
            "motivo_encaminhamento": forms.TextInput(attrs={"placeholder": "Opcional"}),
            "observacoes": forms.Textarea(attrs={"rows": 3, "placeholder": "Notas gerais sobre o encontro"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # RadioSelect não deve ter opção em branco ("---------").
        self.fields["duracao"].choices = Encontro.Duracao.choices
        self.fields["combinados_anteriores"].choices = Encontro.Combinados.choices
        self.fields["presente"].initial = True
        self.fields["aluno"].error_messages["required"] = "Busque e selecione um aluno."
        for nome, campo in self.fields.items():
            if not isinstance(campo.widget, (forms.RadioSelect, forms.CheckboxSelectMultiple, forms.HiddenInput)):
                campo.widget.attrs.setdefault("class", "form-control")
        self.fields["encaminhamento"].widget.attrs["class"] = "form-select"

    def clean(self):
        dados = super().clean()
        aluno = dados.get("aluno")
        if not aluno:
            return dados

        numero = Encontro.proximo_numero(aluno)
        self.instance.numero = numero

        # Combinados anteriores: 1º encontro é automático; depois exige resposta.
        if numero == 1:
            dados["combinados_anteriores"] = Encontro.Combinados.PRIMEIRO
        elif dados.get("presente") and dados.get("combinados_anteriores") in (None, "", Encontro.Combinados.PRIMEIRO):
            self.add_error("combinados_anteriores", "Informe se o aluno cumpriu os combinados anteriores.")

        if dados.get("presente"):
            if not dados.get("duracao"):
                self.add_error("duracao", "Informe a duração do encontro.")
        else:
            # Ausência: não faz sentido guardar duração nem temas.
            dados["duracao"] = ""
            dados["temas"] = []
            if dados.get("combinados_anteriores") == Encontro.Combinados.PRIMEIRO and numero > 1:
                dados["combinados_anteriores"] = ""

        if dados.get("encaminhamento") == Encontro.Encaminhamento.NAO:
            dados["motivo_encaminhamento"] = ""
        return dados

    def save(self, commit=True):
        self.instance.numero = Encontro.proximo_numero(self.cleaned_data["aluno"])
        return super().save(commit=commit)
