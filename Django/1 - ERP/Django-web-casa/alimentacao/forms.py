from django import forms
from django.contrib.auth.models import User
from .models import Alimento, Refeicao, TabelaNutricional
from estoque.models import Estoque 
import datetime

# ========================================================
# 1. FORMULÁRIO DE CARDÁPIO (MENU)
# ========================================================
class AlimentoForm(forms.ModelForm):
    class Meta:
        model = Alimento
        fields = ['nome', 'classificacao', 'calorias']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do Item'}),
            'classificacao': forms.Select(attrs={'class': 'form-select'}),
            'calorias': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0'}),
        }

# ========================================================
# 2. FORMULÁRIO DE DIÁRIO (HISTÓRICO)
# ========================================================
class RefeicaoForm(forms.ModelForm):
    # --- CAMPO NOVO: Seleção de Usuários ---
    para_quem = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True).order_by('first_name'),
        required=False,
        label="Atribuir a:",
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select', 
            'size': '3',
            'style': 'height: auto;'
        }),
        help_text="Segure Ctrl para selecionar vários. Se vazio, será para você."
    )

    data = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        initial=datetime.date.today
    )
    
    class Meta:
        model = Refeicao
        fields = ['data', 'tipo', 'alimentos', 'descricao_adicional', 'observacoes']
        
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            
            # SelectMultiple estilizado
            'alimentos': forms.SelectMultiple(attrs={
                'class': 'form-select', 
                'size': '8', 
                'style': 'height: auto;'
            }),
            
            'descricao_adicional': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Complemento (Ex: Com salada extra)'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Como se sentiu?'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('usuario', None) 
        super().__init__(*args, **kwargs)
        
        if user:
            self.fields['alimentos'].queryset = Alimento.objects.filter(usuario=user).order_by('nome')
        
        self.fields['alimentos'].label_from_instance = self.format_alimento_label
        self.fields['alimentos'].help_text = "Segure Ctrl (PC) ou toque (Celular) para selecionar vários itens."

    def format_alimento_label(self, obj):
        """ Formata a exibição no Dropdown com Emojis """
        icon = ""
        if obj.classificacao == 'SAUDAVEL':
            icon = "✅"
        elif obj.classificacao == 'LIXO':
            icon = "❌"
        else:
            icon = "⚠️"
            
        return f"{icon} {obj.nome} ({obj.calorias} kcal)"

# ========================================================
# 3. FORMULÁRIO DE NUTRIÇÃO (NOVO)
# ========================================================
class TabelaNutricionalForm(forms.ModelForm):
    class Meta:
        model = TabelaNutricional
        fields = ['proteinas', 'carboidratos', 'gorduras_totais', 'acucares', 'sodio', 'fibras']
        widgets = {
            'proteinas': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.1'}),
            'carboidratos': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.1'}),
            'gorduras_totais': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.1'}),
            'acucares': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.1'}),
            'sodio': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '1'}),
            'fibras': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.1'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Torna os campos opcionais no formulário para não dar erro de validação se a pessoa não preencher
        for field in self.fields:
            self.fields[field].required = False