from django import forms
from django.utils import timezone
from .models import Disciplina, AtividadeEstudo, TopicoConteudo, Avaliacao
from usuarios.models import Perfil

class DisciplinaForm(forms.ModelForm):
    class Meta:
        model = Disciplina
        # Adicionei 'curso_catalogo' para permitir vincular a cursos da Netflix
        fields = ['nome', 'categoria', 'professor', 'meta_nota', 'cor_etiqueta', 'curso_catalogo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Matemática ou Curso de Python'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'professor': forms.TextInput(attrs={'class': 'form-control'}),
            'meta_nota': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'cor_etiqueta': forms.TextInput(attrs={'class': 'form-control form-control-color', 'type': 'color'}),
            'curso_catalogo': forms.Select(attrs={'class': 'form-select'}),
        }

class AtividadeEstudoForm(forms.ModelForm):
    class Meta:
        model = AtividadeEstudo
        fields = ['disciplina', 'titulo', 'tipo', 'data_agendada', 'hora_inicio', 'pontos_xp', 'concluido']
        widgets = {
            'disciplina': forms.Select(attrs={'class': 'form-select'}),
            'titulo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Pág 10 a 20'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'data_agendada': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'hora_inicio': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'pontos_xp': forms.NumberInput(attrs={'class': 'form-control'}),
            'concluido': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            # Tenta filtrar apenas disciplinas do usuário logado (ou dependentes)
            # Se der erro, remova este bloco try/except temporariamente
            try:
                self.fields['disciplina'].queryset = Disciplina.objects.filter(usuario=user)
            except:
                pass

class TopicoConteudoForm(forms.ModelForm):
    class Meta:
        model = TopicoConteudo
        fields = ['disciplina', 'nome', 'nivel', 'observacao', 'concluido']
        widgets = {
            'disciplina': forms.Select(attrs={'class': 'form-select'}),
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dúvida específica'}),
            'nivel': forms.Select(attrs={'class': 'form-select'}),
            'observacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'concluido': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class AvaliacaoForm(forms.ModelForm):
    class Meta:
        model = Avaliacao
        # CORREÇÃO CRÍTICA: Mudamos 'nota' para 'nota_obtida'
        fields = ['disciplina', 'descricao', 'data', 'nota_obtida', 'nota_maxima']
        widgets = {
            'disciplina': forms.Select(attrs={'class': 'form-select'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Prova Mensal'}),
            'data': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            # Campo atualizado para nota_obtida
            'nota_obtida': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': 'Sua nota'}),
            'nota_maxima': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'value': 10.0}),
        }