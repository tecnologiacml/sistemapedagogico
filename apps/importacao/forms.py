from django import forms

from apps.alunos.models import Aluno

from .services import TAMANHO_MAXIMO


class UploadCSVForm(forms.Form):
    arquivo = forms.FileField(label="Arquivo CSV")
    unidade = forms.ChoiceField(
        required=False,
        label="Unidade padrão (opcional)",
        choices=[("", "— Sem unidade padrão —")] + list(Aluno.Unidade.choices),
        help_text="Usada só para os alunos que vierem sem unidade no arquivo. "
        "Se deixar em branco, eles são cadastrados sem unidade.",
    )
    atualizar_existentes = forms.BooleanField(
        required=False,
        label="Atualizar alunos que já estão cadastrados",
        help_text="Desmarcado: alunos já cadastrados são rejeitados como duplicados. "
        "Marcado: os campos preenchidos no arquivo alteram o cadastro existente.",
    )

    def clean_arquivo(self):
        arq = self.cleaned_data["arquivo"]
        if not arq.name.lower().endswith(".csv"):
            raise forms.ValidationError("Envie um arquivo .csv (no Excel: Salvar como > CSV).")
        if arq.size > TAMANHO_MAXIMO:
            raise forms.ValidationError("O arquivo passa de 5 MB.")
        return arq