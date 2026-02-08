# carro/forms.py
from django import forms
from .models import Veiculo

class VeiculoForm(forms.ModelForm):
    class Meta:
        model = Veiculo
        # O proprietário é inserido automaticamente na View
        fields = ['nome', 'marca', 'modelo', 'placa', 'ano', 
                  'consumo_cidade_gasolina', 'consumo_estrada_gasolina',
                  'consumo_cidade_etanol', 'consumo_estrada_etanol', 
                  'autorizado_a_usar'] 
        
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'marca': forms.TextInput(attrs={'class': 'form-control'}),
            'modelo': forms.TextInput(attrs={'class': 'form-control'}),
            'placa': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: ABC-1234'}),
            'ano': forms.NumberInput(attrs={'class': 'form-control'}),
            'consumo_cidade_gasolina': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'consumo_estrada_gasolina': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'consumo_cidade_etanol': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'consumo_estrada_etanol': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'autorizado_a_usar': forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        }