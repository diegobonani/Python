from django.contrib import admin
from .models import RotinaPadrao, TarefaDiaria, HistoricoCastigo

# 1. Configuração do Molde (Rotina Padrão)
@admin.register(RotinaPadrao)
class RotinaPadraoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'pontuacao_base', 'horario_sugerido')
    search_fields = ('nome', 'descricao')
    filter_horizontal = ('usuarios_padrao',) # Facilita adicionar vários usuários

# 2. Configuração das Tarefas Diárias
@admin.register(TarefaDiaria)
class TarefaDiariaAdmin(admin.ModelAdmin):
    list_display = ('rotina', 'usuario', 'data_tarefa', 'status', 'pontos_ganhos', 'prazo_hora')
    list_filter = ('data_tarefa', 'status', 'usuario')
    search_fields = ('rotina__nome', 'usuario__username')
    date_hierarchy = 'data_tarefa' # Cria navegação por data no topo

# 3. Configuração dos Castigos
@admin.register(HistoricoCastigo)
class HistoricoCastigoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'motivo', 'gravidade', 'pontos_perdidos', 'data_ocorrencia', 'cumprido')
    list_filter = ('cumprido', 'gravidade', 'usuario')
    search_fields = ('motivo', 'usuario__username')
    list_editable = ('cumprido',) # Permite marcar como cumprido direto na lista