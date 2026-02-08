from django import forms
from .models import Dispositivo

class DispositivoForm(forms.ModelForm):
    class Meta:
        model = Dispositivo
        fields = ['usuario', 'nome', 'mac_address', 'tipo', 'status', 'castigo_ate']
        widgets = {
            'usuario': forms.Select(attrs={'class': 'form-select'}),
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: TV da Sala'}),
            'mac_address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00:11:22:33:44:55', 'data-mask': 'AA:AA:AA:AA:AA:AA'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'castigo_ate': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }

    def clean_mac_address(self):
        # Padroniza para Maiúsculas
        return self.cleaned_data['mac_address'].upper()