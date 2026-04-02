# Em: lavanderia/urls.py

from django.urls import path
from . import views # Importa todas as views do app

# --- MUDANÇA 1: Adiciona o app_name para consertar o erro 'namespace' ---
app_name = 'lavanderia' 

urlpatterns = [
    
    # ===================================================================
    # === 1. VIEWS DE GESTÃO (ADMINISTRADORES / SUPER USERS) ===
    # (Todas estas URLs são apenas para Gestão)
    # ===================================================================
    
    # Página Principal
    path('gerenciar/', views.gerenciar_lavanderia, name='gerenciar_lavanderia'),
    
    # ---- Views de ABAS ----
    path('ajax/aba-ciclos/', views.aba_ciclos_hoje_partial, name='aba_ciclos_hoje_partial'),
    path('ajax/aba-historico/', views.aba_historico_lavanderia_partial, name='aba_historico_lavanderia_partial'),
    
    # ---- Ações para CESTOS (Editar/Excluir) ----
    path('cesto/json/<int:pk>/', views.cesto_detalhes_json, name='cesto_detalhes_json'),
    path('cesto/editar/<int:pk>/', views.cesto_editar, name='cesto_editar'),
    path('cesto/excluir/<int:pk>/', views.cesto_excluir, name='cesto_excluir'),
    
    # ---- Ações para CICLOS (a "Máquina Virtual") ----
    path('ciclo/iniciar/', views.iniciar_ciclo_lavagem, name='iniciar_ciclo_lavagem'),
    path('ciclo/avancar-etapa/<int:pk>/', views.avancar_etapa_ciclo, name='avancar_etapa_ciclo'),
    path('ciclo/adicionar-produto/<int:pk>/', views.adicionar_produto_ciclo, name='adicionar_produto_ciclo'),
    path('ciclo/remover-produto/<int:pk>/', views.remover_produto_ciclo, name='remover_produto_ciclo'),

    # ===================================================================
    # === 2. VIEWS DE USUÁRIO COMUM ===
    # (Nenhuma, conforme solicitado)
    # ===================================================================
]