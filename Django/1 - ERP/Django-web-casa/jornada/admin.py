# Em: jornada/admin.py

from django.contrib import admin
from .models import RegistroPonto, RegistroBalanço, Materia, Nota

# Registra o modelo de Ponto
@admin.register(RegistroPonto)
class RegistroPontoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'data', 'tipo_dia', 'entrada', 'saida', 'horas_trabalhadas', 'horas_extras', 'valor_receber')
    list_filter = ('usuario', 'tipo_dia', 'data')
    search_fields = ('usuario__username', 'data')

# --- NOVO REGISTRO PARA BALANÇO ---
@admin.register(RegistroBalanço)
class RegistroBalançoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'data', 'loja', 'entrada', 'saida', 'horas_trabalhadas', 'valor_receber')
    list_filter = ('usuario', 'loja', 'data')
    search_fields = ('usuario__username', 'loja', 'data')

# --- Registros de Estudo (permanecem iguais) ---
@admin.register(Materia)
class MateriaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'nome', 'professor')
    list_filter = ('usuario',)

@admin.register(Nota)
class NotaAdmin(admin.ModelAdmin):
    list_display = ('materia', 'descricao', 'nota_obtida', 'nota_maxima', 'data_avaliacao')
    list_filter = ('materia__usuario', 'materia')