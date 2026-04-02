from django.urls import path
from . import views

app_name = 'alimentacao'

urlpatterns = [
    # ==========================================================
    # 1. PÁGINA PRINCIPAL E API DE GRÁFICOS
    # ==========================================================
    # Dashboard com Abas
    path('gerenciar/', views.gerenciar_alimentacao, name='gerenciar_alimentacao'),
    
    # API para os Gráficos (Rosca de Calorias e Barras de Macros) - ESTA LINHA FALTAVA
    path('api/check-duplicidade/', views.api_check_duplicidade, name='api_check_duplicidade'),
    path('api/resumo-hoje/', views.api_resumo_nutricional, name='api_resumo_nutricional'),

    # ==========================================================
    # 2. ROTAS PARA O DASHBOARD ADMINISTRATIVO (MODAIS)
    # ==========================================================
    # Lista geral de usuários (Modal Grande)
    path('admin/tabela-parcial/', views.tabela_alimentacao_partial, name='tabela_alimentacao_partial'),
    
    # Histórico detalhado (Drill-down / Modal Pequeno)
    path('admin/historico/<int:user_id>/', views.historico_nutricional_partial, name='historico_nutricional_partial'),
    
    # ==========================================================
    # 3. ROTAS PARA A ABA "MENU / ALIMENTOS" (CRUD AJAX)
    # ==========================================================
    # Carrega a tabela filtrada
    path('menu/tabela/', views.tabela_alimentos_partial, name='tabela_alimentos_partial'),
    
    # Salvar (Criar ou Editar) Alimento
    path('menu/salvar/', views.salvar_alimento, name='salvar_alimento'),
    
    # Obter dados de um alimento (para preencher o modal de edição)
    path('menu/get/<int:pk>/', views.get_alimento_json, name='get_alimento_json'),
    
    # Excluir Alimento
    path('menu/excluir/<int:pk>/', views.excluir_alimento, name='excluir_alimento'),

    # ==========================================================
    # 4. ROTAS PARA A ABA "DIÁRIO / HISTÓRICO" (CRUD AJAX)
    # ==========================================================
    # Carrega a lista histórica (timeline)
    path('diario/tabela/', views.tabela_historico_partial, name='tabela_historico_partial'),
    
    # Registrar nova refeição
    path('diario/salvar/', views.salvar_refeicao, name='salvar_refeicao'),
    
    # Obter dados para edição
    path('diario/get/<int:pk>/', views.get_refeicao_json, name='get_refeicao_json'),
    
    # Excluir registro do diário
    path('diario/excluir/<int:pk>/', views.excluir_refeicao, name='excluir_refeicao'),
]