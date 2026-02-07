from django.urls import path
from . import views

app_name = 'rotinas'

urlpatterns = [
    # Página Principal
    path('gerenciar/', views.gerenciar_rotinas, name='gerenciar_rotinas'),

    # Ações de Botões e Modais (Formulários)
    path('criar-massa/', views.criar_tarefa_massa, name='criar_tarefa_massa'),
    path('aplicar-castigo/', views.aplicar_castigo, name='aplicar_castigo'),
    path('liberar-castigo/<int:pk>/', views.liberar_castigo, name='liberar_castigo'),

    # --- ROTAS CHAMADAS PELO JAVASCRIPT (AJAX) ---
    
    # 1. No HTML chama: 'atualizar_status_tarefa'
    #    Na View é: atualizar_status_ajax
    path('atualizar-status/<int:pk>/', views.atualizar_status_ajax, name='atualizar_status_tarefa'),

    # 2. No HTML chama: 'admin_editar_tarefa'
    #    Na View é: admin_editar_tarefa
    path('admin-editar/<int:pk>/', views.admin_editar_tarefa, name='admin_editar_tarefa'),

    # 3. No HTML chama: 'get_ultimo_castigo'
    #    Na View é: get_ultimo_castigo_ajax
    path('api/ultimo-castigo/', views.get_ultimo_castigo_ajax, name='get_ultimo_castigo'),
    path('importar-rotina/', views.importar_rotina_passada, name='importar_rotina_passada'),
]