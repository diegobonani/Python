from django.contrib import admin
from .models import (
    Unidade, 
    Setor, 
    EstoqueSegmento, 
    EstoqueCategoria, 
    Pet, 
    EquipamentoCategoria, 
    Equipamento,
    Imovel,      # Novo
    Comodo,      # Novo (Movido do Estoque)
    Localizacao  # Novo (Movido do Estoque)
)

# --- Registros Simples ---
admin.site.register(Unidade)
admin.site.register(Setor)
admin.site.register(EstoqueSegmento)
admin.site.register(Pet)
admin.site.register(EquipamentoCategoria)

# --- Admin de Estoque Categoria ---
@admin.register(EstoqueCategoria)
class EstoqueCategoriaAdmin(admin.ModelAdmin):
    list_display = ('nome_categoria', 'get_segmentos')
    search_fields = ('nome_categoria',)
    list_filter = ('segmentacao',) 
    filter_horizontal = ('segmentacao',) 
    ordering = ('nome_categoria',)

    @admin.display(description="Visibilidade")
    def get_segmentos(self, obj):
        return ", ".join([s.nome_segmento for s in obj.segmentacao.all()])

# --- Admin de Equipamento ---
@admin.register(Equipamento)
class EquipamentoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'categoria', 'localizacao', 'mac_address')
    list_filter = ('categoria', 'localizacao')
    search_fields = ('nome', 'mac_address', 'modelo', 'marca')
    ordering = ('categoria', 'nome')

# ===================================================================
# NOVO: ADMINISTRAÇÃO DOS IMÓVEIS E CÔMODOS
# ===================================================================

class ComodoInline(admin.TabularInline):
    model = Comodo
    extra = 1
    classes = ('collapse',) # Deixa recolhido para não poluir

@admin.register(Imovel)
class ImovelAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo', 'finalidade', 'cidade', 'eh_condominio')
    list_filter = ('tipo', 'finalidade', 'eh_condominio', 'cidade')
    search_fields = ('nome', 'logradouro', 'nome_condominio')
    
    # Organização Visual dos Campos (Fieldsets)
    fieldsets = (
        ('Identificação', {
            'fields': ('nome', 'tipo', 'finalidade', 'observacoes')
        }),
        ('Endereço', {
            'fields': (('logradouro', 'numero'), 'complemento', ('bairro', 'cidade', 'uf'), 'cep')
        }),
        ('Detalhes de Condomínio / Vertical', {
            'classes': ('collapse',), # Clica para expandir
            'fields': ('eh_condominio', 'nome_condominio', ('bloco_torre', 'quadra'), ('andar', 'unidade_apto'))
        }),
        ('Características', {
            'fields': (('metragem', 'qtd_comodos_estimada'),)
        }),
    )
    inlines = [ComodoInline] # Permite criar Cômodos direto na tela do Imóvel

class LocalizacaoInline(admin.TabularInline):
    model = Localizacao
    extra = 1

@admin.register(Comodo)
class ComodoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'imovel', 'count_locais')
    list_filter = ('imovel',)
    search_fields = ('nome', 'imovel__nome')
    inlines = [LocalizacaoInline] # Permite criar Prateleiras dentro do Cômodo

    @admin.display(description="Locais")
    def count_locais(self, obj):
        return obj.localizacoes.count()

@admin.register(Localizacao)
class LocalizacaoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'comodo', 'get_imovel')
    search_fields = ('nome', 'comodo__nome')
    list_filter = ('comodo__imovel',)

    @admin.display(description="Imóvel")
    def get_imovel(self, obj):
        return obj.comodo.imovel.nome if obj.comodo.imovel else "-"