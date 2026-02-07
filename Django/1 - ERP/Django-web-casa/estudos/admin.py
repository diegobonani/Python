import os
import re
import asyncio
import time
import math
from django.contrib import admin
from django.contrib import messages
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect, StreamingHttpResponse
from django.contrib.admin import helpers
from django.db import connections 
from telethon.sync import TelegramClient 

from usuarios.models import Perfil

from .models import (
    Disciplina, AtividadeEstudo, TopicoConteudo, Avaliacao,
    GradeCurricular, Matricula, DiarioBordo,
    AreaConhecimento, Especialidade, Curso, ModuloCurso, Aula, ProgressoAula
)

# ==========================================================
# CONFIGURAÇÕES DO TELEGRAM
# ==========================================================
API_ID = 36604823
API_HASH = '2787b098e6a8caf60fa6e460a1dd24e5'
CHANNEL_ID = -1003842800000 

# ==========================================================
# 1. FUNÇÕES AUXILIARES
# ==========================================================
def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]

def html_console_header(titulo):
    return f"""
    <html>
    <head>
        <style>
            body {{ background-color: #1e1e1e; color: #d4d4d4; font-family: 'Consolas', 'Monaco', monospace; padding: 20px; font-size: 14px; }}
            .log-entry {{ margin-bottom: 4px; border-bottom: 1px solid #333; padding-bottom: 2px; }}
            .success {{ color: #4ec9b0; }}
            .warning {{ color: #cca700; }}
            .error {{ color: #f44747; }}
            .info {{ color: #569cd6; }}
            .upload {{ color: #c586c0; font-weight: bold; }}
            .highlight {{ color: #ce9178; font-weight: bold; }}
        </style>
    </head>
    <body>
    <h2>🚀 Console: {titulo}</h2>
    <hr style='border-color: #333;'>
    """

# ==========================================================
# 2. MOTOR: IMPORTAÇÃO LOCAL
# ==========================================================
def stream_local_scan(curso, pasta_raiz, simular):
    yield html_console_header(f"Scan Local - {curso.titulo}")
    
    if not os.path.exists(pasta_raiz):
        yield "<h3 class='error'>❌ Pasta não encontrada!</h3></body></html>"
        return

    try:
        itens = sorted(os.listdir(pasta_raiz), key=natural_sort_key)
        for mod_nome in itens:
            path_mod = os.path.join(pasta_raiz, mod_nome)
            if not os.path.isdir(path_mod): continue

            yield f"<div class='log-entry'>📂 Módulo: {mod_nome}</div>"
            
            ordem_mod = 100
            try:
                nums = ''.join(filter(str.isdigit, mod_nome.split()[0]))
                if nums: ordem_mod = int(nums)
            except: pass

            mod_obj = None
            if not simular:
                mod_obj, _ = ModuloCurso.objects.get_or_create(
                    curso=curso, titulo=mod_nome, defaults={'ordem': ordem_mod}
                )

            arquivos = []
            for root, dirs, files in os.walk(path_mod):
                for f in files:
                    if f.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.ts')):
                        arquivos.append(os.path.join(root, f))
            arquivos.sort(key=lambda f: natural_sort_key(os.path.basename(f)))

            for i, path_video in enumerate(arquivos, 1):
                nome_base = os.path.splitext(os.path.basename(path_video))[0]
                nome_limpo = re.sub(r'^[\d\.\-\s]+', '', nome_base.replace('_', ' ')) or nome_base
                titulo_final = f"{i:02d}. {nome_limpo}"

                caminho_relativo = ""
                path_lower = path_video.lower()
                if 'media' in path_lower:
                    idx = path_lower.find('catalogo') 
                    if idx == -1: idx = path_lower.find('media')
                    if idx != -1: caminho_relativo = path_video[idx:]

                status = "🔍 Detectado"
                if not simular and mod_obj:
                    aula, created = Aula.objects.get_or_create(
                        modulo=mod_obj, titulo=titulo_final, defaults={'ordem': i}
                    )
                    if caminho_relativo:
                        aula.video_arquivo.name = caminho_relativo.replace('\\', '/')
                        aula.save()
                    status = "✅ Salvo (Local)"

                yield f"&nbsp;&nbsp;🎬 {titulo_final} <span class='success'>[{status}]</span><br>"

        yield "<br><h3 class='success'>🏁 Fim do Scan Local.</h3>"
        yield "<a href='/admin/estudos/curso/' style='background:white; color:black; padding:5px;'>Voltar</a></body></html>"
    except Exception as e:
        yield f"<h3 class='error'>Erro: {e}</h3>"


# ==========================================================
# 3. MOTOR: UPLOAD TELEGRAM (COM SINCRONIA DE RESERVA)
# ==========================================================
def stream_telegram_upload(curso, pasta_raiz, simular):
    yield html_console_header(f"UPLOAD TELEGRAM - {curso.titulo}")
    
    yield """
    <script>
        function showRetry(msg) {
            document.getElementById('retry-box').style.display = 'block';
            document.getElementById('error-msg').innerText = msg;
            window.scrollTo(0, document.body.scrollHeight);
        }
        function updateStatus(text) {
            document.getElementById('status-bar').innerText = text;
        }
    </script>
    <div id='status-bar' style='position:fixed; top:0; left:0; width:100%; background:#417690; color:white; padding:5px; text-align:center; font-weight:bold; z-index:999;'>Iniciando...</div>
    <div id='retry-box' style='display:none; background:#ffdddd; border:2px solid red; padding:20px; margin:20px 0; border-radius:8px;'>
        <h3 style='color:red; margin-top:0;'>⚠️ A Conexão caiu ou houve um erro!</h3>
        <p id='error-msg' style='color:#333;'></p>
        <button onclick='location.reload()' style='background:red; color:white; padding:15px 30px; border:none; font-size:16px; cursor:pointer; font-weight:bold; border-radius:5px;'>🔄 TENTAR NOVAMENTE</button>
    </div>
    <br><br>
    """
    
    connections.close_all()

    try:
        if os.name == 'nt':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    except Exception as e:
        yield f"<script>showRetry('Erro ao criar Loop: {e}')</script>"
        return

    if simular:
        yield "<h3 class='info'>🧪 MODO SIMULAÇÃO</h3>"

    client = TelegramClient('sessao_admin', API_ID, API_HASH, loop=loop)
    
    try:
        if not simular:
            yield "<div class='info'>🔌 Conectando (Sessão Admin)...</div>"
            client.connect()
            if not client.is_user_authorized():
                yield "<h3 class='error'>❌ ERRO: 'sessao_admin.session' não autenticada!</h3>"
                return
            yield "<div class='success'>✅ Conectado!</div><hr>"
    except Exception as e:
        yield f"<script>showRetry('Erro Conexão: {e}')</script>"
        if not client.is_connected(): client.disconnect()
        return

    try:
        itens = sorted(os.listdir(pasta_raiz), key=natural_sort_key)
        
        for mod_nome in itens:
            path_mod = os.path.join(pasta_raiz, mod_nome)
            if not os.path.isdir(path_mod): continue

            yield f"<div class='log-entry' style='margin-top:20px; color: cyan;'>📂 Módulo: {mod_nome}</div>"
            yield f"<script>updateStatus('Processando: {mod_nome}...')</script>"

            ordem_mod = 100
            try:
                nums = ''.join(filter(str.isdigit, mod_nome.split()[0]))
                if nums: ordem_mod = int(nums)
            except: pass
            
            mod_obj = None
            if not simular:
                try:
                    mod_obj, _ = ModuloCurso.objects.get_or_create(
                        curso=curso, titulo=mod_nome, defaults={'ordem': ordem_mod}
                    )
                except:
                     connections.close_all()
                     time.sleep(0.5)
                     mod_obj, _ = ModuloCurso.objects.get_or_create(
                        curso=curso, titulo=mod_nome, defaults={'ordem': ordem_mod}
                     )

            arquivos = []
            for root, dirs, files in os.walk(path_mod):
                for f in files:
                    if f.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.ts')):
                        arquivos.append(os.path.join(root, f))
            arquivos.sort(key=lambda f: natural_sort_key(os.path.basename(f)))

            for i, path_video in enumerate(arquivos, 1):
                nome_base = os.path.splitext(os.path.basename(path_video))[0]
                nome_limpo = re.sub(r'^[\d\.\-\s]+', '', nome_base.replace('_', ' ')) or nome_base
                titulo_final = f"{i:02d}. {nome_limpo}"

                # === LÓGICA DE SINCRONIA AVANÇADA ===
                ja_existe = False
                esta_sendo_processado = False
                
                if mod_obj:
                    connections.close_all() # Atualiza visão do banco
                    aula_db = Aula.objects.filter(modulo=mod_obj, titulo=titulo_final).first()
                    
                    if aula_db:
                        link = aula_db.video_link or ""
                        if "tg://" in link:
                            ja_existe = True
                        elif "http://uploading" in link:
                            esta_sendo_processado = True

                if ja_existe:
                    yield f"&nbsp;&nbsp;⏭️ {titulo_final} <span class='success'>[JÁ ENVIADO]</span><br>"
                    continue
                
                if esta_sendo_processado:
                     yield f"&nbsp;&nbsp;⏳ {titulo_final} <span class='warning'>[PROCESSANDO POR OUTRO SCRIPT...]</span><br>"
                     continue

                try:
                    tamanho_bytes = os.path.getsize(path_video)
                    tamanho_mb = tamanho_bytes / (1024 * 1024)
                    str_tamanho = f"{tamanho_mb:.2f} MB"
                except: str_tamanho = "?"

                yield f"&nbsp;&nbsp;☁️ <span class='upload'>SUBINDO: {titulo_final} </span> <span class='info'>[{str_tamanho}]</span>... "
                yield f"<script>updateStatus('Subindo: {titulo_final} ({str_tamanho})'); window.scrollTo(0, document.body.scrollHeight);</script>"

                if not simular:
                    try:
                        # 1. RESERVA A VAGA NO BANCO (LOCK)
                        # Assim, se o script passar aqui agora, ele vai ver "uploading" e pular
                        Aula.objects.update_or_create(
                            modulo=mod_obj,
                            titulo=titulo_final,
                            defaults={
                                'ordem': i,
                                'video_link': 'http://uploading', # <--- O SEGREDO
                                'video_arquivo': path_video.split('catalogo')[-1].replace('\\', '/') if 'catalogo' in path_video else ''
                            }
                        )
                        
                        # 2. FAZ O UPLOAD
                        if not client.is_connected():
                            yield "<span class='warning'>[Reconectando...]</span> "
                            client.connect()

                        caption = f"#{curso.especialidade.area.nome} > {curso.titulo}\n📂 {mod_nome}\n🎬 {titulo_final}"
                        
                        msg = client.send_file(
                            CHANNEL_ID,
                            path_video,
                            caption=caption,
                            force_document=False,
                            supports_streaming=True
                        )
                        
                        link_tg = f"tg://{CHANNEL_ID}/{msg.id}"
                        
                        # 3. ATUALIZA COM O LINK REAL
                        connections.close_all()
                        aula_obj = Aula.objects.get(modulo=mod_obj, titulo=titulo_final)
                        aula_obj.video_link = link_tg
                        aula_obj.save()
                        
                        yield "<span class='success'>✅ OK!</span><br>"
                        time.sleep(0.5)

                    except Exception as e:
                        # SE DER ERRO, LIBERA A VAGA
                        if mod_obj:
                             try:
                                 connections.close_all()
                                 aula_fail = Aula.objects.filter(modulo=mod_obj, titulo=titulo_final).first()
                                 if aula_fail and aula_fail.video_link == 'http://uploading':
                                     aula_fail.video_link = '' # Libera para tentar de novo depois
                                     aula_fail.save()
                             except: pass

                        err_str = str(e)
                        yield f"<br><span class='error'>❌ FALHA: {e}</span><br>"
                        yield f"<script>showRetry('{e}')</script>"
                        break 
                else:
                    yield "<span class='info'>[SIMULADO]</span><br>"
                    time.sleep(0.1)

    except Exception as e:
         yield f"<script>showRetry('Erro Fatal: {e}')</script>"
    finally:
        if not simular and client.is_connected():
            client.disconnect()
        
    yield "<br><hr><h1 class='success'>🎉 UPLOAD COMPLETO!</h1>"
    yield "<script>updateStatus('Concluído!');</script>"
    yield "<a href='/admin/estudos/curso/' style='background:#4ec9b0; color:black; padding:10px; text-decoration:none;'>⬅️ Voltar para Cursos</a></body></html>"

# ==========================================================
# 4. ADMIN CONFIG
# ==========================================================
@admin.register(Matricula)
class MatriculaAdmin(admin.ModelAdmin):
    list_display = ('aluno', 'ano_serie_atual', 'nivel_atual', 'ano_letivo')
    list_filter = ('ano_letivo', 'nivel_atual')
    search_fields = ('aluno__nome_completo',)
    autocomplete_fields = ['aluno']

@admin.register(GradeCurricular)
class GradeCurricularAdmin(admin.ModelAdmin):
    list_display = ('disciplina', 'ano_serie', 'nivel')

@admin.register(DiarioBordo)
class DiarioBordoAdmin(admin.ModelAdmin):
    list_display = ('get_aluno', 'disciplina_base')
    def get_aluno(self, obj): return obj.matricula.aluno.nome_completo

@admin.register(AreaConhecimento)
class AreaAdmin(admin.ModelAdmin):
    list_display = ('nome',)
    search_fields = ('nome',)

@admin.register(Especialidade)
class EspecialidadeAdmin(admin.ModelAdmin):
    list_display = ('nome', 'area')
    list_filter = ('area',)
    search_fields = ('nome',)
    autocomplete_fields = ['area']

@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'especialidade', 'total_modulos')
    search_fields = ('titulo',)
    list_filter = ('especialidade__area', 'especialidade')
    autocomplete_fields = ['especialidade']
    
    actions = ['acao_importar_local', 'acao_upload_telegram', 'acao_distribuir_selecionados']

    class ModuloInline(admin.TabularInline):
        model = ModuloCurso
        extra = 0
        fields = ('ordem', 'titulo')
    inlines = [ModuloInline]

    def total_modulos(self, obj): return obj.modulos.count()

    @admin.action(description='📂 1. Importar Caminho Local (Rápido)')
    def acao_importar_local(self, request, queryset):
        return self.render_import_screen(request, queryset, "local")

    @admin.action(description='☁️ 2. Fazer Upload para Telegram (Completo)')
    def acao_upload_telegram(self, request, queryset):
        return self.render_import_screen(request, queryset, "telegram")

    @admin.action(description='👥 3. Distribuir Curso (Selecionar Alunos)')
    def acao_distribuir_selecionados(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Selecione apenas 1 curso.", level=messages.WARNING)
            return None
        
        curso = queryset.first()

        if 'apply' in request.POST:
            perfis_ids = request.POST.getlist('perfis')
            if not perfis_ids:
                self.message_user(request, "Nenhum aluno selecionado.", level=messages.WARNING)
                return HttpResponseRedirect(request.get_full_path())

            categoria = 'EXTRA'
            nome_area = curso.especialidade.area.nome.upper()
            if 'IDIOMA' in nome_area or 'LINGUA' in nome_area: categoria = 'IDIOMAS'
            elif 'ESCOLA' in nome_area: categoria = 'ESCOLA'

            criados = 0
            for pid in perfis_ids:
                perfil = Perfil.objects.get(id=pid)
                _, created = Disciplina.objects.get_or_create(
                    usuario=perfil.usuario,
                    curso_catalogo=curso,
                    defaults={'nome': curso.titulo, 'categoria': categoria}
                )
                if created: criados += 1
            
            self.message_user(request, f"✅ Curso distribuído para {criados} alunos.")
            return HttpResponseRedirect(request.get_full_path())

        alunos = Perfil.objects.filter(esta_estudando=True) | Perfil.objects.filter(esta_fazendo_curso=True)
        alunos = alunos.distinct().order_by('nome_completo')
        
        context = {
            'curso': curso, 'alunos': alunos,
            'opts': self.model._meta, 'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
        }
        return render(request, 'estudos/distribuir_curso.html', context)

    def render_import_screen(self, request, queryset, modo):
        if queryset.count() != 1:
            self.message_user(request, "Selecione apenas 1 curso.", level=messages.WARNING)
            return None
        curso = queryset.first()
        if 'apply' in request.POST:
            caminho = request.POST.get('caminho_pasta')
            simular = request.POST.get('simular') == 'on'
            if not caminho:
                self.message_user(request, "Caminho inválido.", level=messages.ERROR)
                return HttpResponseRedirect(request.get_full_path())
            if modo == "local": generator = stream_local_scan(curso, caminho, simular)
            else: generator = stream_telegram_upload(curso, caminho, simular)
            response = StreamingHttpResponse(generator)
            response['Content-Type'] = 'text/html'
            return response
        
        titulo_tela = "📂 Importar Apenas Localmente" if modo == "local" else "☁️ Upload para Telegram & Banco"
        ajuda_tela = "Mapeia arquivos locais." if modo == "local" else "Envia vídeos para o Telegram."
        context = {
            'curso': curso, 'modo': modo, 'titulo_tela': titulo_tela, 'ajuda_tela': ajuda_tela,
            'opts': self.model._meta, 'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
        }
        return render(request, 'estudos/importar_pasta.html', context)

@admin.register(ModuloCurso)
class ModuloCursoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'curso', 'total_aulas')
    search_fields = ('titulo',)
    autocomplete_fields = ['curso']
    def total_aulas(self, obj): return obj.aulas.count()

@admin.register(Aula)
class AulaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'modulo')
    search_fields = ('titulo',)
    autocomplete_fields = ['modulo']

@admin.register(Disciplina)
class DisciplinaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'usuario', 'categoria', 'curso_catalogo') 
    list_filter = ('categoria', 'usuario')
    search_fields = ('nome', 'usuario__first_name', 'curso_catalogo__titulo')
    autocomplete_fields = ['curso_catalogo'] 

@admin.register(AtividadeEstudo)
class AtividadeEstudoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'disciplina', 'data_agendada', 'concluido')
    list_filter = ('concluido', 'data_agendada')
    autocomplete_fields = ['disciplina']

@admin.register(ProgressoAula)
class ProgressoAulaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'aula', 'concluido', 'data_conclusao')
    list_filter = ('usuario', 'concluido')
    search_fields = ('usuario__first_name', 'aula__titulo')
    autocomplete_fields = ['aula', 'usuario']

admin.site.register(Avaliacao)
admin.site.register(TopicoConteudo)