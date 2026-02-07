from django import forms
from .models import DiaDeDeslocamento, LocalizacaoFrequente
from carro.models import Veiculo
from django.db.models import Q
import datetime

class DiaDeDeslocamentoForm(forms.ModelForm):
    # Campo oculto para o JSON da rota (required=False permite edição sem mudar rota)
    enderecos_waypoints = forms.CharField(
        widget=forms.HiddenInput(), 
        required=False
    )
    
    data = forms.DateField(
        label="Data",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        input_formats=['%Y-%m-%d'],
        initial=datetime.date.today
    )

    # --- CAMPOS DE COMBUSTÍVEL E CÁLCULO ---

    tipo_combustivel = forms.ChoiceField(
        choices=DiaDeDeslocamento.TIPO_COMBUSTIVEL_CHOICES,
        label="Combustível",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # NOVO: Tipo de Trajeto (Cidade/Estrada/Misto)
    tipo_trajeto = forms.ChoiceField(
        choices=DiaDeDeslocamento.TIPO_TRAJETO_CHOICES,
        label="Trajeto",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    valor_litro = forms.DecimalField(
        label="Preço Litro (R$)",
        max_digits=5, decimal_places=2,
        widget=forms.NumberInput(attrs={'step': 0.01, 'class': 'form-control', 'placeholder': 'Ex: 5.49'})
    )

    # Consumo Manual (Opcional - Sobrescreve o cadastro do veículo)
    consumo_manual = forms.DecimalField(
        label="Consumo Manual (Km/L)",
        required=False,
        help_text="Preencha para ignorar o cadastro do veículo.",
        widget=forms.NumberInput(attrs={'step': 0.1, 'class': 'form-control', 'placeholder': 'Opcional'})
    )

    # Observações
    observacoes = forms.CharField(
        label="Observações",
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )

    class Meta:
        model = DiaDeDeslocamento
        # Lista completa de campos que serão manipulados
        fields = [
            'veiculo', 'data', 'tipo_combustivel', 
            'valor_litro', 'tipo_trajeto', 'consumo_manual', 'observacoes'
        ]

    def __init__(self, *args, **kwargs):
        usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)
        
        if usuario:
            # Filtra veículos do usuário
            self.fields['veiculo'].queryset = Veiculo.objects.filter(
                Q(proprietario=usuario) | Q(autorizado_a_usar=usuario)
            ).distinct()
            # Adiciona classe Bootstrap ao select de veículo
            self.fields['veiculo'].widget.attrs.update({'class': 'form-select'})

    def clean(self):
        cleaned_data = super().clean()
        veiculo = cleaned_data.get('veiculo')
        consumo_manual = cleaned_data.get('consumo_manual')
        valor_litro = cleaned_data.get('valor_litro')

        # Regra de Negócio:
        # Precisa ter um Veículo (para pegar o consumo do cadastro) 
        # OU um Consumo Manual digitado.
        if not veiculo and not consumo_manual:
            self.add_error('veiculo', "Selecione um veículo ou informe o consumo manual.")
            
        # O preço do combustível é sempre obrigatório para calcular o custo R$
        if valor_litro is None or valor_litro <= 0:
             self.add_error('valor_litro', "Informe o preço do combustível.")

        return cleaned_data