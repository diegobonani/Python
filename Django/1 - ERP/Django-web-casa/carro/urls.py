from django.urls import path
from . import views

app_name = 'carro'

urlpatterns = [
    path('', views.gerenciar_veiculo, name='gerenciar_veiculo'),
    path('salvar/', views.salvar_veiculo, name='salvar_veiculo'),
    path('excluir/<int:veiculo_id>/', views.excluir_veiculo, name='excluir_veiculo'),
    path('obter/<int:veiculo_id>/', views.obter_veiculo, name='obter_veiculo'),
]