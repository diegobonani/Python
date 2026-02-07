# Em deslocamento/admin.py

from django.contrib import admin
# MUDANÇA AQUI: Corrigindo Deslocamento para DiaDeDeslocamento
from .models import DiaDeDeslocamento, Abastecimento 

# 1. Registro do modelo Abastecimento
@admin.register(Abastecimento)
class AbastecimentoAdmin(admin.ModelAdmin):
    list_display = ('veiculo', 'data', 'km_odometro', 'litros', 'valor_total')
    list_filter = ('veiculo', 'data')
    search_fields = ('veiculo__placa',)
    
# 2. Registro do modelo DiaDeDeslocamento (CORRIGIDO)
@admin.register(DiaDeDeslocamento)
class DiaDeDeslocamentoAdmin(admin.ModelAdmin):
    list_display = ('data', 'veiculo', 'origem_display', 'destino_display', 'km_total_apurado', 'custo_total_estimado')
    list_filter = ('veiculo', 'data', 'tipo_trajeto') # Usando 'data' e 'tipo_trajeto' que existem
    search_fields = ('veiculo__placa', 'observacoes')