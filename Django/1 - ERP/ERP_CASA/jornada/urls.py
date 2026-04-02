# Em: jornada/urls.py

from django.urls import path
from . import views

app_name = 'jornada'

urlpatterns = [
    # ===================================================================
    # === 1. URLS DE GESTÃO (ADMINISTRADORES / SUPER USERS) ===
    # ===================================================================
    
    path('gerenciar-jornada/', views.gerenciar_jornada_view, name='gerenciar_jornada'),
    path('gerenciar-estudos/', views.gerenciar_estudos_view, name='gerenciar_estudos'),
    
    # --- AJAX (Jornada) ---
    path('gerenciar/ponto/adicionar/', views.admin_registrar_ponto_ajax, name='admin_registrar_ponto_ajax'),
    path('gerenciar/ponto/get/<int:pk>/', views.admin_get_ponto_json, name='admin_get_ponto_json'),
    path('gerenciar/ponto/editar/<int:pk>/', views.admin_editar_ponto_ajax, name='admin_editar_ponto_ajax'),
    path('gerenciar/ponto/deletar/<int:pk>/', views.admin_deletar_ponto_ajax, name='admin_deletar_ponto_ajax'),
    
    # --- AJAX (Balanço) - NOVO ---
    path('gerenciar/balanco/adicionar/', views.admin_registrar_balanco_ajax, name='admin_registrar_balanco_ajax'),
    path('gerenciar/balanco/get/<int:pk>/', views.admin_get_balanco_json, name='admin_get_balanco_json'),
    path('gerenciar/balanco/editar/<int:pk>/', views.admin_editar_balanco_ajax, name='admin_editar_balanco_ajax'),
    path('gerenciar/balanco/deletar/<int:pk>/', views.admin_deletar_balanco_ajax, name='admin_deletar_balanco_ajax'),
    
    # --- Exportação ---
    path('gerenciar/exportar-csv/', views.exportar_jornada_csv, name='exportar_jornada_csv'),
    path('gerenciar/exportar-pdf/<int:pk>/', views.exportar_registro_pdf, name='exportar_registro_pdf'),
    path('gerenciar/exportar-pdf-relatorio/', views.exportar_jornada_pdf, name='exportar_jornada_pdf'),
    
    # ===================================================================
    # === 2. URLS DE USUÁRIO COMUM ===
    # ===================================================================
    
    # --- Meu Trabalho ---
    path('meu-trabalho/', views.meu_trabalho_view, name='meu_trabalho'),
    path('bater-ponto/', views.bater_ponto_ajax, name='bater_ponto_ajax'),
    path('registrar-ponto/', views.registrar_ponto_ajax, name='registrar_ponto_ajax'),
    path('get-ponto/<int:pk>/', views.get_ponto_json, name='get_ponto_json'),
    path('editar-ponto/<int:pk>/', views.editar_ponto_ajax, name='editar_ponto_ajax'),
    path('deletar-ponto/<int:pk>/', views.deletar_ponto_ajax, name='deletar_ponto_ajax'),
    
    # --- Meus Estudos ---
    path('meus-estudos/', views.meus_estudos_view, name='meus_estudos'),
    path('adicionar-materia/', views.adicionar_materia_ajax, name='adicionar_materia_ajax'),
    path('deletar-materia/<int:pk>/', views.deletar_materia_ajax, name='deletar_materia_ajax'),
    path('adicionar-nota/', views.adicionar_nota_ajax, name='adicionar_nota_ajax'),
    path('deletar-nota/<int:pk>/', views.deletar_nota_ajax, name='deletar_nota_ajax'),
]