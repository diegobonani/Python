# Em: financas/forms.py

from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User

# Imports dos modelos deste app (Limpo)
from .models import Financa, ContaFinanceira, FinancaCategoria, CenarioFinanceiro
from deslocamento.models import Abastecimento
from carro.models import Manutencao

class ContaFinanceiraForm(forms.ModelForm):
    """
    Formulário para Criar e Editar Contas Financeiras (usado pelo Superuser).
    """
    class Meta:
        model = ContaFinanceira
        fields = ['nome', 'saldo_inicial', 'usuario', 'nao_permite_negativo']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nome'].widget.attrs.update({'class': 'form-control'})
        self.fields['saldo_inicial'].widget.attrs.update({'class': 'form-control'})
        self.fields['usuario'].widget.attrs.update({'class': 'form-select'})
        self.fields['nao_permite_negativo'].widget.attrs.update({'class': 'form-check-input'})


class FinancaForm(forms.ModelForm):
    """
    Formulário principal de Lançamento (Receita/Despesa).
    """
    
    # Campo 'usuario' visível apenas para Gestores
    usuario = forms.ModelChoiceField(
        queryset=User.objects.all().order_by('username'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False 
    )

    class Meta:
        model = Financa
        fields = [
            'usuario', 'conta', 'nome', 'descricao', 'categoria', 
            'tipo', 'conta_tipo', 'valor', 'forma_pagamento', 'data_registro'
        ]
        widgets = {
            'data_registro': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.usuario_logado = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)

        is_gestor = False
        if self.usuario_logado:
            # Lógica para determinar se o usuário é um Gestor/Admin
            is_gestor = self.usuario_logado.is_superuser or \
                         self.usuario_logado.groups.filter(name='Administradores').exists()
        
        # Aplica classes bootstrap
        for field_name, field in self.fields.items():
            if field_name != 'data_registro':
                css_class = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
                field.widget.attrs['class'] = css_class
        
        # Lógica de filtragem baseada em Papel
        if is_gestor:
            # LÓGICA DO GESTOR
            self.fields['usuario'].required = True
            self.fields['usuario'].queryset = User.objects.all().order_by('username')
            self.fields['conta'].queryset = ContaFinanceira.objects.all().order_by('usuario__username', 'nome')
        else:
            # LÓGICA DO PEÃO
            del self.fields['usuario']
            self.fields['conta'].queryset = ContaFinanceira.objects.filter(usuario=self.usuario_logado).order_by('nome')
        
    def clean(self):
        cleaned_data = super().clean()
        conta = cleaned_data.get("conta")
        tipo = cleaned_data.get("tipo")
        valor = cleaned_data.get("valor")

        if conta and tipo and valor:
            if conta.nao_permite_negativo and tipo == 'Despesas':
                saldo_a_verificar = conta.saldo_atual
                if self.instance and self.instance.pk:
                    # Se for uma edição de uma despesa, "devolve" o valor antigo para o cálculo
                    if self.instance.tipo == 'Despesas':
                        saldo_a_verificar += self.instance.valor
                
                if (saldo_a_verificar - valor) < 0:
                    raise ValidationError(
                        f"Saldo insuficiente na conta '{conta.nome}'. "
                        f"Saldo atual: R$ {conta.saldo_atual}. "
                        f"Você não pode registrar uma despesa de R$ {valor}."
                    )
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        is_gestor = False
        if self.usuario_logado:
            is_gestor = self.usuario_logado.is_superuser or \
                         self.usuario_logado.groups.filter(name='Administradores').exists()

        if is_gestor:
            # Para o Gestor, o campo 'usuario' do formulário já define instance.usuario
            pass 
        else:
            # Para o Usuário Comum, forçamos o usuário logado
            instance.usuario = self.usuario_logado
        
        if commit:
            instance.save()
        return instance

class CenarioFinanceiroForm(forms.ModelForm):
    class Meta:
        model = CenarioFinanceiro
        fields = ['titulo', 'tipo', 'valor_total', 'valor_entrada', 'poupanca_mensal_planejada']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Casa Própria'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'valor_total': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'valor_entrada': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'poupanca_mensal_planejada': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Ex: 1500.00'}),
        }