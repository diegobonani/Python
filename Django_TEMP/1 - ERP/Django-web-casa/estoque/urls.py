from django.urls import path
from . import views

app_name = 'estoque'

urlpatterns = [
    # ===================================================================
    # 1. VISÃO GERAL / ESTOQUE FÍSICO (CRUD E TABELA)
    # ===================================================================
    path('gerenciar/', views.gerenciar_estoque, name='gerenciar_estoque'),
    path('meu-estoque/', views.meu_estoque_view, name='meu_estoque_view'),
    
    # Carregamento da Tabela (AJAX)
    path('ajax/tabela-unificada/', views.tabela_estoque_unificada_partial, name='tabela_estoque_unificada_partial'),

    # Ações do Item (CRUD)
    path('ajax/item/<int:pk>/json/', views.get_item_json, name='get_item_json'),
    path('ajax/item/<int:pk>/editar/', views.editar_estoque_item, name='editar_estoque_item'),
    path('ajax/item/<int:pk>/baixa/', views.dar_baixa_item, name='dar_baixa_item'),
    path('ajax/item/<int:pk>/deletar/', views.deletar_estoque_item, name='deletar_estoque_item'),

    # ===================================================================
    # 2. COMPRAS
    # ===================================================================
    path('compras/registrar/', views.registrar_compra_ajax, name='registrar_compra_ajax'),
    path('compras/ler-nota/', views.ler_nota_ajax, name='ler_nota_ajax'),
    
    # JSON e Dados Auxiliares
    path('compras/json/<int:pk>/', views.get_compra_json, name='get_compra_json'),
    path('compras/itens-json/<int:pk>/', views.get_compra_itens_json, name='get_compra_itens_json'),
    
    # Ações de Edição/Exclusão
    path('compras/editar/<int:pk>/', views.editar_compra_ajax, name='editar_compra_ajax'),
    path('compras/deletar/<int:pk>/', views.deletar_compra_ajax, name='deletar_compra_ajax'),
    
    # Detalhes (Visualização HTML)
    path('compras/detalhes/<int:pk>/', views.lista_compra_detalhe, name='lista_compra_detalhe'),

    # ===================================================================
    # 3. FINANCEIRO (INTEGRAÇÃO)
    # ===================================================================
    path('compras/lancar-despesa/<int:pk>/', views.lancar_despesa_compra_ajax, name='lancar_despesa_compra_ajax'),
    path('compras/reverter-lancamento/<int:pk>/', views.reverter_lancamento_compra_ajax, name='reverter_lancamento_compra_ajax'),

    # ===================================================================
    # 4. HISTÓRICO
    # ===================================================================
    path('ajax/historico/', views.aba_historico_estoque_partial, name='aba_historico_estoque_partial'),

    # ===================================================================
    # 5. IMPORTAÇÃO
    # ===================================================================
    path('importar/', views.importar_nota_view, name='importar_nota'),
    path('importar/processar/', views.processar_importacao_view, name='processar_importacao'),

    # ===================================================================
    # 6. SIMULAÇÃO E ASSISTENTE
    # ===================================================================
    path('ajax/simulacao/', views.aba_simulacao_partial, name='aba_simulacao_partial'),
    
    path('catalogo/gerenciar/', views.gerenciar_catalogo_pessoal, name='gerenciar_catalogo_pessoal'),
    path('faltantes/adicionar/', views.adicionar_item_faltante, name='adicionar_item_faltante'),
    path('faltantes/<int:pk>/remover/', views.remover_item_faltante, name='remover_item_faltante'),
    
    path('cenario/<int:pk>/', views.simulacao_cenario_detalhe, name='simulacao_cenario_detalhe'),

    # ===================================================================
    # 7. HELPERS AJAX (DROPDOWNS INTERNOS)
    # ===================================================================
    path('ajax/get-filtro-opcoes/', views.get_filtro_opcoes, name='get_filtro_opcoes'),
    path('ajax/get-categorias/', views.get_categorias_por_setor, name='get_categorias_por_setor'),
    path('ajax/get-destinatarios/', views.get_destinatarios_json, name='get_destinatarios_json'),
    path('ajax/get-localizacoes/', views.get_localizacoes_json, name='get_localizacoes_json'),
    path('ajax/get-comodos-imovel/', views.get_comodos_por_imovel, name='get_comodos_por_imovel'),

    # ===================================================================
    # 8. APIS DE INTEGRAÇÃO (USADAS PELA ALIMENTAÇÃO)
    # ===================================================================
    path('api/get-locais-com-alimentos/', views.api_get_locais_alimentos, name='api_get_locais'),
    path('api/get-itens-por-local/<int:local_id>/', views.api_get_itens_por_local, name='api_get_itens'),
]