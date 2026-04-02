from django.urls import path
from . import views

app_name = 'rede'

urlpatterns = [
    path('gerenciar/', views.gerenciar_rede, name='gerenciar_rede'),
    path('salvar/', views.salvar_dispositivo, name='salvar_dispositivo'),
    path('bloquear/<int:pk>/', views.alternar_bloqueio, name='alternar_bloqueio'),
    path('excluir/<int:pk>/', views.excluir_dispositivo, name='excluir_dispositivo'),
]