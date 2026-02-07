from django.contrib import admin
from django.urls import path, include
from django.conf import settings             # <--- Necessário para ler o MEDIA_ROOT
from django.conf.urls.static import static   # <--- Necessário para criar a URL dos arquivos

# 1. Importe as views do seu app 'usuarios'
from usuarios import views as usuarios_views

urlpatterns = [
    path('admin/', admin.site.urls),

    path('core/', include('core.urls')), 

    # 2. Rota raiz (/) aponta para o login
    path('', usuarios_views.logar_usuario, name='login'),
    
    # 3. Rota de logout
    path('logout/', usuarios_views.deslogar_usuario, name='logout'),

    # 4. As URLs de 'dashboard', 'ajax', etc.
    path('usuarios/', include('usuarios.urls')),

    # 5. Mantenha os includes dos seus outros apps
    path('alimentacao/', include('alimentacao.urls', namespace='alimentacao')),
    path('deslocamento/', include('deslocamento.urls', namespace='deslocamento')),
    path('estoque/', include('estoque.urls')),
    path('estudos/', include('estudos.urls')),
    path('financas/', include('financas.urls')),
    path('rotinas/', include('rotinas.urls')),
    path('lavanderia/', include('lavanderia.urls')),
    path('jornada/', include('jornada.urls')),
    path('rede/', include('rede.urls')),
    path('veiculos/', include('carro.urls')),
]

# --- CONFIGURAÇÃO PARA SERVIR ARQUIVOS DE MÍDIA (VÍDEOS) ---
# Isso é obrigatório para que os vídeos dos cursos funcionem localmente
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)