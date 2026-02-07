from django.contrib import admin
from .models import Veiculo, Servico, Manutencao # 1. Importar Manutencao

@admin.register(Veiculo)
class VeiculoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'marca', 'modelo', 'placa', 'km_atual')
    search_fields = ('nome', 'marca', 'modelo', 'placa')
    readonly_fields = ('km_atual',)

@admin.register(Servico)
class ServicoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'veiculo', 'ultima_km', 'ultima_data', 'intervalo_km', 'intervalo_dias')
    list_filter = ('veiculo',)
    search_fields = ('nome',)
    readonly_fields = ('ultima_km', 'ultima_data')

# 2. Registrar o modelo Manutencao
@admin.register(Manutencao)
class ManutencaoAdmin(admin.ModelAdmin):
    # CORRIGIDO: usando os nomes exatos do seu Manutencao/models.py
    list_display = ('veiculo', 'data_servico', 'km_odometro', 'servico_realizado', 'custo_total') 
    
    # CORRIGIDO: list_filter e search_fields também usam os nomes exatos
    list_filter = ('veiculo', 'servico_realizado', 'data_servico')
    search_fields = ('veiculo__placa', 'servico_realizado__nome')