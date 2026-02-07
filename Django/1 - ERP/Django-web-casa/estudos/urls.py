from django.urls import path
from . import views

app_name = 'estudos'

urlpatterns = [
    # --- PAINÉIS PRINCIPAIS ---
    path('visao-geral/', views.visao_geral_familia, name='visao_geral'),
    path('gerenciar/', views.gerenciar_estudos, name='gerenciar_estudos'),
    
    # --- API PLAYER (NOVO - FUNDAMENTAL PARA O MODAL) ---
    # Busca os dados do vídeo (URL, Título, Próxima Aula) via AJAX
    path('api/player/<int:aula_id>/', views.api_aula_player, name='api_aula_player'),

    # --- AÇÕES DE CRIAÇÃO (MODAIS) ---
    path('adicionar/disciplina/', views.adicionar_disciplina, name='adicionar_disciplina'),
    path('adicionar/atividade/', views.adicionar_atividade, name='adicionar_atividade'),
    path('adicionar/dificuldade/', views.adicionar_dificuldade, name='adicionar_dificuldade'),
    path('adicionar/avaliacao/', views.adicionar_avaliacao, name='adicionar_avaliacao'),
    
    # --- AÇÕES DE EDIÇÃO E EXCLUSÃO ---
    path('editar/disciplina/<int:disciplina_id>/', views.editar_disciplina, name='editar_disciplina'),
    path('excluir/disciplina/<int:disciplina_id>/', views.excluir_disciplina, name='excluir_disciplina'),

    # --- AÇÕES DE PROCESSAMENTO ---
    path('salvar-notas/', views.salvar_notas, name='salvar_notas'),
    path('registrar-grupo/', views.registrar_estudo_grupo, name='registrar_estudo_grupo'),

    # --- ROTAS LEGADO (Mantidas para compatibilidade de links antigos) ---
    # Agora redirecionam para o gerenciador, pois o player é um Modal na mesma tela
    path('curso/<int:disciplina_id>/play/', views.assistir_curso, name='iniciar_curso'),
    path('curso/<int:disciplina_id>/aula/<int:aula_id>/', views.assistir_curso, name='assistir_aula'),

    # --- API AUXILIAR (QUESTÕES) ---
    path('api/gerar-questoes/', views.api_gerar_questoes, name='api_gerar_questoes'),
]