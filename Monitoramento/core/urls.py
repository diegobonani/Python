from django.contrib import admin
from django.urls import path
from contas.views import dashboard, sair 

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', dashboard, name='dashboard'),
    path('sair/', sair, name='logout') #Ao clicar no botão sair, vai redirecionar para a tela de login 
]