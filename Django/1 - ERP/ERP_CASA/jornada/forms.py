# Em: jornada/forms.py

from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.utils import timezone 
from .models import RegistroPonto, RegistroBalanço, Materia, Nota, TipoDiaJornada
import datetime 

# ===================================================================
# === 1. FORMULÁRIOS PARA A ABA "JORNADA" ===
# ===================================================================

class RegistroPontoForm(forms.ModelForm):
    """
    Formulário para a aba JORNADA (Ponto Normal).
    """
    class Meta:
        model = RegistroPonto
        fields = [
            'data', 'tipo_dia', 
            'entrada', 'saida_almoco', 'retorno_almoco', 'saida',
            'atestado_cid', 'atestado_crm', 'atestado_obs'
        ]
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'tipo_dia': forms.Select(attrs={'class': 'form-select'}), 
            'entrada': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'saida_almoco': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'retorno_almoco': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'saida': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            
            'atestado_cid': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Z76.5'}),
            'atestado_crm': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '123456/SP'}),
            'atestado_obs': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Ex: Consulta médica...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            data_inicial = timezone.now().date()
            self.fields['data'].initial = data_inicial
            if data_inicial.weekday() == 5: # Sábado
                self.initial['tipo_dia'] = TipoDiaJornada.SABADO
            elif data_inicial.weekday() == 6: # Domingo
                self.initial['tipo_dia'] = TipoDiaJornada.FOLGA
            else:
                self.initial['tipo_dia'] = TipoDiaJornada.NORMAL

    def clean(self):
        """ Validação e Lógica de Atestado/Folga """
        cleaned_data = super().clean()
        
        tipo_dia = cleaned_data.get('tipo_dia')
        data = cleaned_data.get('data')

        if not data:
            return cleaned_data

        # === LÓGICA DE ATESTADO (COMPENSAÇÃO) ===
        if tipo_dia == TipoDiaJornada.ATESTADO:
            day_of_week = data.weekday()
            
            # Se for Sábado (5)
            if day_of_week == 5:
                # Compensação de Sábado (06:30 - 10:30, 4h, SEM almoço)
                cleaned_data['entrada'] = datetime.time(6, 30)
                cleaned_data['saida_almoco'] = None
                cleaned_data['retorno_almoco'] = None
                cleaned_data['saida'] = datetime.time(10, 30)
            # Se for Domingo (6)
            elif day_of_week == 6:
                # Compensação de Plantão (06:30 - 12:00, 5.5h, SEM almoço)
                cleaned_data['entrada'] = datetime.time(6, 30)
                cleaned_data['saida_almoco'] = None
                cleaned_data['retorno_almoco'] = None
                cleaned_data['saida'] = datetime.time(12, 0)
            else: # Dia de Semana (0-4)
                # Compensação de Dia de Semana (08:00 - 18:00 c/ 2h almoço)
                cleaned_data['entrada'] = datetime.time(8, 0)
                cleaned_data['saida_almoco'] = datetime.time(12, 0)
                cleaned_data['retorno_almoco'] = datetime.time(14, 0)
                cleaned_data['saida'] = datetime.time(18, 0)
            
            return cleaned_data # Pula as validações de horário

        # === LÓGICA DE FOLGA ===
        if tipo_dia == TipoDiaJornada.FOLGA:
            cleaned_data['entrada'] = None
            cleaned_data['saida_almoco'] = None
            cleaned_data['retorno_almoco'] = None
            cleaned_data['saida'] = None
            cleaned_data['atestado_cid'] = None
            cleaned_data['atestado_crm'] = None
            cleaned_data['atestado_obs'] = None
            return cleaned_data

        # --- Se NÃO for Atestado, limpa os campos de atestado ---
        cleaned_data['atestado_cid'] = None
        cleaned_data['atestado_crm'] = None
        cleaned_data['atestado_obs'] = None
        
        # --- Se for Sábado, etc. (sem almoço), limpa os campos de almoço ---
        if tipo_dia != TipoDiaJornada.NORMAL:
            cleaned_data['saida_almoco'] = None
            cleaned_data['retorno_almoco'] = None

        # --- Validação de Horários ---
        entrada = cleaned_data.get('entrada')
        saida = cleaned_data.get('saida')

        if tipo_dia == TipoDiaJornada.NORMAL:
            saida_almoco = cleaned_data.get('saida_almoco')
            retorno_almoco = cleaned_data.get('retorno_almoco')
            if entrada and saida_almoco and saida_almoco < entrada:
                raise ValidationError("A 'Saída Almoço' não pode ser antes da 'Entrada'.")
            if saida_almoco and retorno_almoco and retorno_almoco < saida_almoco:
                raise ValidationError("O 'Retorno Almoço' não pode ser antes da 'Saída Almoço'.")
            if retorno_almoco and saida and saida < retorno_almoco:
                raise ValidationError("A 'Saída' final não pode ser antes do 'Retorno Almoço'.")
        else: # Sábado, Feriado, Plantão
            if entrada and saida and saida < entrada:
                 raise ValidationError("A 'Saída' final não pode ser antes da 'Entrada'.")
                
        return cleaned_data


class RegistroPontoAdminForm(RegistroPontoForm):
    """ Formulário para GESTORES (permite escolher o usuário). """
    usuario = forms.ModelChoiceField(
        queryset=User.objects.filter(perfil__esta_trabalhando=True).order_by('username'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Colaborador"
    )
    class Meta(RegistroPontoForm.Meta):
        fields = ['usuario'] + RegistroPontoForm.Meta.fields


# ===================================================================
# === 2. FORMULÁRIOS PARA A ABA "BALANÇO" ===
# ===================================================================

class RegistroBalançoForm(forms.ModelForm):
    """
    Formulário específico para a aba BALANÇO.
    """
    class Meta:
        model = RegistroBalanço
        fields = ['data', 'loja', 'entrada', 'saida', 'anexo']
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'loja': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Loja 01 - Centro'}),
            'entrada': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'saida': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'anexo': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['data'].initial = timezone.now().date()
            
    def clean(self):
        cleaned_data = super().clean()
        entrada = cleaned_data.get('entrada')
        saida = cleaned_data.get('saida')
        
        if entrada and saida and saida < entrada:
            raise ValidationError("A 'Saída' não pode ser antes da 'Entrada'.")
        return cleaned_data

class RegistroBalançoAdminForm(RegistroBalançoForm):
    """ Versão do Admin para o formulário de Balanço. """
    usuario = forms.ModelChoiceField(
        queryset=User.objects.filter(perfil__esta_trabalhando=True).order_by('username'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Colaborador"
    )
    class Meta(RegistroBalançoForm.Meta):
        fields = ['usuario'] + RegistroBalançoForm.Meta.fields


# ===================================================================
# === 3. FORMULÁRIOS PARA O "MODO ESTUDO" ===
# ===================================================================
# (MateriaForm e NotaForm permanecem iguais)

class MateriaForm(forms.ModelForm):
    class Meta:
        model = Materia
        fields = ['nome']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Matemática'})
        }

class NotaForm(forms.ModelForm):
    class Meta:
        model = Nota
        fields = ['materia', 'descricao', 'nota_obtida', 'nota_maxima']
        widgets = {
            'materia': forms.Select(attrs={'class': 'form-select'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Prova Mensal'}),
            'nota_obtida': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'nota_maxima': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
        }

    def __init__(self, *args, **kwargs):
        usuario_logado = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)
        if usuario_logado:
            self.fields['materia'].queryset = Materia.objects.filter(usuario=usuario_logado).order_by('nome')