from django.urls import path
from . import views

app_name = 'deslocamento'

urlpatterns = [
    # VIEW PRINCIPAL (Painel de Gerenciamento)
    path('gerenciar/', views.gerenciar_deslocamentos, name='gerenciar_deslocamentos'),
    
    # ENDPOINTS AJAX DE CRIAÇÃO
    # Usado para submeter o formulário (cria o DiaDeDeslocamento + Percursos)
    path('registrar_dia/', views.registrar_dia_deslocamento, name='registrar_dia_deslocamento'),
    
    # ENDPOINTS AJAX DE LEITURA/LISTAGEM
    # Usado para carregar a tabela DataTables
    path('resumo_partial/', views.resumo_deslocamento_partial, name='resumo_deslocamento_partial'),
    # Usado para carregar os detalhes dos trechos no modal
    path('detalhes_percurso/<int:pk>/', views.detalhes_percurso_ajax, name='detalhes_percurso_ajax'),
    
    # ENDPOINTS AJAX DE EDIÇÃO E EXCLUSÃO
    # Retorna o JSON de um registro para preencher o formulário de edição
    path('json/<int:pk>/', views.get_deslocamento_json, name='get_deslocamento_json'),
    # Processa a submissão do formulário de edição
    path('editar/<int:pk>/', views.editar_deslocamento_ajax, name='editar_deslocamento_ajax'),
    # Exclui o Dia de Deslocamento
    path('deletar/<int:pk>/', views.deletar_deslocamento_ajax, name='deletar_deslocamento_ajax'),

    # Rota existente (opcional, se usada para o JS de autocomplete)
    path('localizacoes_json/', views.localizacoes_json, name='localizacoes_json'),
]