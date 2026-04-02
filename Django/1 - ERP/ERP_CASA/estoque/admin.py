from django.contrib import admin
from .models import (
    Estoque, ItemCasa, ItemPet, ItemUsuario,
    ListaCompra, ListaCompraProduto,
    SimulacaoCenario, SimulacaoItem, EstoqueLog
)
# Nota: Comodo e Localizacao foram removidos daqui pois agora são gerenciados pelo app 'core'

# ==============================================================================
# 1. ADMINS PARA AS TABELAS FILHAS (DETALHES)
# ==============================================================================

@admin.register(ItemCasa)
class ItemCasaAdmin(admin.ModelAdmin):
    # Campos atualizados
    list_display = ('nome', 'comodo', 'localizacao', 'categoria', 'quantidade', 'preco', 'unidade', 'validade')
    list_filter = ('comodo', 'categoria', 'unidade')
    search_fields = ('nome', 'comodo__nome')

@admin.register(ItemPet)
class ItemPetAdmin(admin.ModelAdmin):
    list_display = ('nome', 'pet', 'categoria', 'quantidade', 'unidade', 'preco', 'validade')
    list_filter = ('pet', 'categoria')
    search_fields = ('nome', 'pet__nome_pet')

@admin.register(ItemUsuario)
class ItemUsuarioAdmin(admin.ModelAdmin):
    list_display = ('nome', 'usuario', 'categoria', 'quantidade')
    list_filter = ('usuario', 'categoria')
    search_fields = ('nome', 'usuario__username')

# ==============================================================================
# 2. ADMIN PARA A TABELA PAI (HUB)
# ==============================================================================

@admin.register(Estoque)
class EstoqueAdmin(admin.ModelAdmin):
    list_display = ('id', 'setor', 'get_item_nome', 'get_quantidade', 'data_cadastro')
    list_filter = ('setor', 'data_cadastro')
    search_fields = ('id',)

    def get_item_nome(self, obj):
        if obj.item_casa: return f"[CASA] {obj.item_casa.nome}"
        if obj.item_pet: return f"[PET] {obj.item_pet.nome}"
        if obj.item_usuario: return f"[USER] {obj.item_usuario.nome}"
        return "-"
    get_item_nome.short_description = "Item"

    def get_quantidade(self, obj):
        if obj.item_casa: return f"{obj.item_casa.quantidade} {obj.item_casa.unidade.sigla if obj.item_casa.unidade else ''}"
        if obj.item_pet: return f"{obj.item_pet.quantidade} {obj.item_pet.unidade.sigla if obj.item_pet.unidade else ''}"
        if obj.item_usuario: return f"{obj.item_usuario.quantidade}"
        return "-"
    get_quantidade.short_description = "Qtd"

# ==============================================================================
# 3. OUTROS ADMINS (Auxiliares)
# ==============================================================================

@admin.register(ListaCompra)
class ListaCompraAdmin(admin.ModelAdmin):
    list_display = ('supermercado', 'data_compra', 'valor_total', 'detalhada', 'lancamento_financeiro_criado')
    list_filter = ('data_compra', 'lancamento_financeiro_criado')

@admin.register(ListaCompraProduto)
class ListaCompraProdutoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'compra', 'valor_unit', 'quantidade', 'adicionado_ao_estoque')

@admin.register(EstoqueLog)
class EstoqueLogAdmin(admin.ModelAdmin):
    list_display = ('data_hora', 'usuario', 'acao', 'item_nome', 'item_setor', 'quantidade_antiga', 'quantidade_nova')
    list_filter = ('acao', 'item_setor', 'usuario')
    readonly_fields = ('data_hora',)

@admin.register(SimulacaoCenario)
class SimulacaoCenarioAdmin(admin.ModelAdmin):
    list_display = ('nome', 'usuario_criador', 'data_criacao')

@admin.register(SimulacaoItem)
class SimulacaoItemAdmin(admin.ModelAdmin):
    list_display = ('nome_item', 'cenario', 'preco_estimado', 'quantidade')