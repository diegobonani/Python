from django import forms
from django.contrib.auth.models import User
from django.db.models import Q 
from .models import CestoDeRoupas, CicloLavagem, Equipamento, ProdutoConsumidoLavagem
from estoque.models import Estoque
from core.models import EstoqueCategoria # Importa a Categoria

class CestoDeRoupasForm(forms.ModelForm):
    """ Formulário para Adicionar ou Editar um cesto de roupas sujas. """
    usuario = forms.ModelChoiceField(
        queryset=User.objects.filter(username__in=[
            'diegobonani', 'jessicabarbosa', 'leandroaugusto', 
            'emanuellykamilly', 'elloabeatriz', 'arthurmiguel'
        ]),
        required=False, label="Dono das Roupas",
        help_text="Deixe em branco se for da 'Casa' (cama, mesa, banho) ou do 'Pet'.",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    class Meta:
        model = CestoDeRoupas
        fields = ['usuario', 'tipo_roupa', 'quantidade_cestos', 'prioridade']
        widgets = {
            'tipo_roupa': forms.Select(attrs={'class': 'form-select'}),
            'quantidade_cestos': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.25', 'placeholder': 'Ex: 1.0 (cesto cheio), 0.5 (meio cesto)'}),
            'prioridade': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = { 'quantidade_cestos': 'Quantidade de Cestos (aprox.)' }

    def clean(self):
        cleaned_data = super().clean()
        tipo_roupa = cleaned_data.get('tipo_roupa')
        usuario = cleaned_data.get('usuario')
        if tipo_roupa == 'PET' and usuario is not None:
            self.add_error('usuario', 'Para roupas do Pet, o campo "Dono" deve ficar em branco.')
        elif tipo_roupa == 'CAMA_BANHO' and usuario is not None:
            self.add_error('usuario', 'Para Cama e Banho, o campo "Dono" deve ficar em branco.')
        elif tipo_roupa in ['ESCURAS', 'BRANCAS', 'DELICADAS'] and usuario is None:
            self.add_error('usuario', 'Para este tipo de roupa, você precisa selecionar um Dono.')
        return cleaned_data


class IniciarCicloForm(forms.ModelForm):
    """ Formulário exibido no modal "Iniciar Ciclo". """
    equipamento = forms.ModelChoiceField(
        queryset=Equipamento.objects.filter(capacidade_kg__isnull=False),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Equipamento a ser usado"
    )
    class Meta:
        model = CicloLavagem
        fields = ['equipamento']

class ProdutoConsumidoForm(forms.ModelForm):
    """ Formulário para adicionar produtos a um ciclo JÁ CRIADO. """
    produto_estoque = forms.ModelChoiceField(
        queryset=Estoque.objects.none(), # Será preenchido no __init__
        label="Produto",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    class Meta:
        model = ProdutoConsumidoLavagem
        fields = ['produto_estoque', 'quantidade_consumida']
        widgets = {
            'quantidade_consumida': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtra o estoque para mostrar APENAS os produtos de lavanderia
        segmentos_casa = ['Todos', 'Casa', 'N_Usuarios', 'N_Pets']
        # Presume que suas categorias de estoque se chamam 'Produtos de Lavanderia' ou 'Produtos de Limpeza'
        # e estão corretamente segmentadas no admin do 'core'
        self.fields['produto_estoque'].queryset = Estoque.objects.filter(
            categoria__segmentacao__nome_segmento__in=segmentos_casa
        ).filter(
            Q(categoria__nome_categoria__icontains='Lavanderia') |
            Q(categoria__nome_categoria__icontains='Limpeza')
        ).distinct().order_by('nome_item')