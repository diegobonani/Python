# Arquivo: core/urls.py

from django.urls import path
from . import views

# O namespace 'core' é fundamental para usarmos {% url 'core:...' %} no HTML
app_name = 'core'

urlpatterns = [
    # Rota que abre o Modal (carrega o HTML do formulário)
    path('exportacao/modal/', views.exportacao_modal_view, name='exportacao_modal'),

    # Rota que recebe o POST do formulário e gera o arquivo
    path('exportacao/processar/', views.processar_exportacao_global, name='processar_exportacao'),

    # Rota para salvar a configuração da automação (00:00)
    path('exportacao/config/salvar/', views.salvar_config_global, name='salvar_config'),
]