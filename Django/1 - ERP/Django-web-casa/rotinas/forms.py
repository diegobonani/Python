from django import forms
from django.contrib.auth.models import User
from .models import RotinaPadrao, HistoricoCastigo, TarefaDiaria

class CriarTarefaForm(forms.Form):
    # 1. Qual Rotina?
    rotina = forms.ModelChoiceField(
        queryset=RotinaPadrao.objects.filter(ativa=True),
        label="Rotina / Tarefa",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # 2. Para Quem? (Múltipla escolha)
    usuarios = forms.ModelMultipleChoiceField(
        queryset=User.objects.exclude(is_superuser=True),
        label="Para quem?",
        widget=forms.SelectMultiple(attrs={'class': 'form-select select2-modal', 'style': 'width: 100%'})
    )
    
    # 3. Data de Agendamento
    data_tarefa = forms.DateField(
        label="Data",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    # 4. Horário de Início (Para ordenar na Timeline)
    prazo_hora = forms.TimeField(
        label="Horário Agendado",
        required=False,
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'})
    )

    # 5. DURAÇÃO / CRONÔMETRO (Novos Campos Opcionais)
    duracao_dias = forms.IntegerField(
        initial=0, min_value=0, required=False, 
        label="Dias",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0'})
    )
    duracao_horas = forms.IntegerField(
        initial=0, min_value=0, max_value=23, required=False, 
        label="Horas",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0'})
    )
    duracao_minutos = forms.IntegerField(
        initial=0, min_value=0, max_value=59, required=False, 
        label="Minutos",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0'})
    )

    # 6. Bônus Extra
    pontos_extra_inicial = forms.IntegerField(
        label="Bônus / Valor (Opcional)",
        required=False,
        help_text="Se preenchido, define um valor extra.",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 10'})
    )

# 2. DISCIPLINA (Modal Admin) - Mantido igual ao seu original
class AplicarCastigoForm(forms.ModelForm):
    usuario = forms.ModelChoiceField(
        queryset=User.objects.exclude(is_superuser=True).order_by('username'),
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_castigo_usuario'}),
        label="Quem?"
    )

    class Meta:
        model = HistoricoCastigo
        fields = ['usuario', 'motivo', 'gravidade', 'descricao_detalhada', 'pontos_perdidos', 'data_liberacao', 'cumprido']
        widgets = {
            'usuario': forms.Select(attrs={'class': 'form-select'}),
            'motivo': forms.TextInput(attrs={'class': 'form-control'}),
            'gravidade': forms.Select(attrs={'class': 'form-select'}),
            'descricao_detalhada': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'pontos_perdidos': forms.NumberInput(attrs={'class': 'form-control'}),
            'data_liberacao': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'cumprido': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

    def clean(self):
        cleaned_data = super().clean()
        gravidade = cleaned_data.get('gravidade')
        pontos = cleaned_data.get('pontos_perdidos')
        
        if pontos:
            pts = abs(pontos)
            if gravidade == 'LEVE' and pts > 15:
                self.add_error('pontos_perdidos', "Leve: Máximo 15 pontos.")
            elif gravidade == 'MEDIA' and (pts <= 15 or pts > 40):
                self.add_error('pontos_perdidos', "Média: Entre 16 e 40 pontos.")
            elif gravidade == 'GRAVE' and (pts <= 40 or pts > 80):
                self.add_error('pontos_perdidos', "Grave: Entre 41 e 80 pontos.")
            elif gravidade == 'GRAVISSIMA' and pts <= 80:
                self.add_error('pontos_perdidos', "Gravíssima: Mais de 80 pontos.")
        return cleaned_data