from django.urls import path
from . import views # Importa todas as views do app

# Define um namespace para este app (boa prática)
app_name = 'financas' 

urlpatterns = [
    
    # ===================================================================
    # === 1. URLS DE GESTÃO (ADMINISTRADORES / SUPER USERS) ===
    # ===================================================================
    
    # --- Páginas Principais de Gestão ---
    path('gerenciar/', views.gerenciar_financas, name='gerenciar_financas'),
    path('contas/', views.gerenciar_contas, name='gerenciar_contas'),
   # Rota para a Simulação (Cenários Financeiros)
    path('simulacao/partial/', views.aba_simulacao_financeira_partial, name='aba_simulacao_financeira_partial'),
    
    # Rota para o Detalhe (opcional, se você for usar depois)
    path('simulacao/<int:pk>/', views.simulacao_financeira_detalhe, name='simulacao_financeira_detalhe'),

    # --- Ações de CRUD de CONTAS ---
    # Usadas pelo modal em gerenciar_contas.html
    path('contas/adicionar/', views.adicionar_conta, name='adicionar_conta'), 
    path('contas/editar/<int:pk>/', views.editar_conta, name='editar_conta'),
    path('contas/json/<int:pk>/', views.get_conta_json, name='get_conta_json'), # Retorna dados para o modal de edição

    # --- Ações de CRUD de LANÇAMENTOS (Financa) ---
    path('lancamento/adicionar/', views.adicionar_financa, name='adicionar_financa'),
    path('lancamento/json/<int:pk>/', views.get_financa_json, name='get_financa_json'),
    path('lancamento/editar/<int:pk>/', views.editar_financa, name='editar_financa'),
    path('lancamento/deletar/<int:pk>/', views.deletar_financa, name='deletar_financa'),
    
    # --- Endpoints AJAX e Parciais (Gestão) ---
    path('tabela-financas/', views.tabela_financas_partial, name='tabela_financas_partial'),
    path('get-categorias/', views.get_categorias_por_tipo, name='get_categorias_por_tipo'),
    # Adicione esta linha:
    path('api/get-servicos-veiculo/', views.get_servicos_veiculo, name='get_servicos_veiculo'),
    # Mantive get_conta_saldo_json caso seja usado em outro lugar, mas o get_conta_json deve ser usado para edição completa.
    path('conta/saldo/json/<int:pk>/', views.get_conta_saldo_json, name='get_conta_saldo_json'),

    
    # ===================================================================
    # === 2. URLS DE USUÁRIO COMUM ===
    # ===================================================================
    
    # --- Página "Minhas Finanças" ---
    path('minhas-financas/', views.minhas_financas_view, name='minhas_financas'),
]