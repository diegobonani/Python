# Em: usuarios/urls.py

from django.urls import path
from . import views # Importa as views do app usuarios

urlpatterns = [
    # URLs dos Dashboards
    path('dashboard_admin/', views.dashboard_admin, name='dashboard_admin'),
    path('dashboard_usuario/', views.dashboard_usuario, name='dashboard_usuario'),
    
    # URL de Redirecionamento
    path('redirecionar/', views.redirecionar_usuario, name='redirecionar_usuario'),
    
    # --- URLs de AJAX (Endpoints) ---
    
    # Para os cards do dashboard
    path('update_dashboard_counts/', views.update_dashboard_counts, name='update_dashboard_counts'),
    
    # Para o modal de Usuários
    path('tabela_usuarios_partial/', views.tabela_usuarios_partial, name='tabela_usuarios_partial'),
    
    # --- NOVAS URLS PARA OS OUTROS MODAIS ---
    path('tabela_estoque_partial/', views.tabela_estoque_partial, name='tabela_estoque_partial'),
    path('tabela_financas_partial/', views.tabela_financas_partial, name='tabela_financas_partial'),
    path('tabela_rotinas_partial/', views.tabela_rotinas_partial, name='tabela_rotinas_partial'),
]