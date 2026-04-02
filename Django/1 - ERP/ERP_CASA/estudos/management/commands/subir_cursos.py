import os
import asyncio
import re
from django.core.management.base import BaseCommand
from telethon import TelegramClient
from django.conf import settings
from django.db import close_old_connections # <--- IMPORTANTE: O REMÉDIO PARA O ERRO
from estudos.models import AreaConhecimento, Especialidade, Curso, ModuloCurso, Aula

# ==============================================================================
# CONFIGURAÇÕES
# ==============================================================================
API_ID = 36604823
API_HASH = '2787b098e6a8caf60fa6e460a1dd24e5'
CHANNEL_ID = -1003842800000 

# Caminho Raiz dos Cursos (Seu caminho atual)
PASTA_RAIZ = r"C:\Users\DIEGOBONANI\OneDrive\Desktop\Python\Django\1 - ERP\Django-web-casa\media\catalogo"

# IMPORTANTE: Use a sessão separada para não conflitar com o Admin
client = TelegramClient('sessao_uploader', API_ID, API_HASH)

class Command(BaseCommand):
    help = 'Robô de Cursos com Sistema de Retomada Inteligente (Resume)'

    def handle(self, *args, **kwargs):
        if not os.path.exists(PASTA_RAIZ):
            self.stdout.write(self.style.ERROR(f"Pasta não encontrada: {PASTA_RAIZ}"))
            return
        
        # Ajuste para Windows (Evita erro de Event Loop)
        if os.name == 'nt':
             asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        print(f"🚀 INICIANDO ROBÔ DE CURSOS (SESSÃO UPLOADER)")
        print(f"📂 Lendo de: {PASTA_RAIZ}")
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.processar_pastas())
        except KeyboardInterrupt:
            print("\n🛑 Processo pausado pelo usuário.")
        finally:
            loop.close()

    def natural_sort_key(self, s):
        return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]

    async def processar_pastas(self):
        print("🔌 Conectando ao Telegram...")
        await client.start()
        
        try:
            # Verifica conexão
            me = await client.get_me()
            print(f"✅ Logado como: {me.first_name}")
        except Exception as e:
            print(f"❌ Erro de Login: {e}")
            return

        print("\n📂 Iniciando varredura geral...")

        # 1. ÁREA
        for area_nome in sorted(os.listdir(PASTA_RAIZ)):
            path_area = os.path.join(PASTA_RAIZ, area_nome)
            if not os.path.isdir(path_area): continue
            
            if area_nome in ['uploads_gerais', 'capas', 'System Volume Information', 'KIDS']: continue

            # DB Call: Fecha conexões velhas antes de usar
            area = await asyncio.to_thread(self.get_or_create_area, area_nome)
            especialidade = await asyncio.to_thread(self.get_or_create_esp, "Geral", area)
            
            print(f"📂 [ÁREA] {area_nome}")

            # 2. CURSO
            for curso_nome in sorted(os.listdir(path_area)):
                path_curso = os.path.join(path_area, curso_nome)
                if not os.path.isdir(path_curso): continue

                curso = await asyncio.to_thread(self.get_or_create_curso, curso_nome, especialidade)
                print(f"  🎓 [CURSO] {curso_nome}")

                # 3. MÓDULO
                modulos_ordenados = sorted(os.listdir(path_curso), key=self.natural_sort_key)
                
                for mod_nome in modulos_ordenados:
                    path_mod = os.path.join(path_curso, mod_nome)
                    if not os.path.isdir(path_mod): continue

                    ordem_mod = 100
                    try:
                        numeros = ''.join(filter(str.isdigit, mod_nome.split()[0]))
                        if numeros: ordem_mod = int(numeros)
                    except: pass

                    # DB Call: Criar Módulo
                    modulo = await asyncio.to_thread(self.get_or_create_modulo, mod_nome, curso, ordem_mod)

                    # 4. AULAS
                    arquivos_video = []
                    for root, dirs, files in os.walk(path_mod):
                        for file in files:
                            if file.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.ts')):
                                arquivos_video.append(os.path.join(root, file))
                    
                    arquivos_video.sort(key=lambda f: self.natural_sort_key(os.path.basename(f)))
                    
                    if not arquivos_video: continue

                    # Lista o que já existe no banco
                    titulos_existentes = await asyncio.to_thread(self.get_titulos_existentes, modulo)
                    
                    arquivos_pendentes = []

                    for i, path_video_completo in enumerate(arquivos_video, start=1):
                        video_nome_original = os.path.basename(path_video_completo)
                        nome_base = os.path.splitext(video_nome_original)[0].replace('_', ' ')
                        nome_limpo = re.sub(r'^[\d\.\-\s]+', '', nome_base) or nome_base
                        titulo_final = f"{i:02d}. {nome_limpo}"

                        if titulo_final in titulos_existentes:
                            pass # Já existe
                        else:
                            arquivos_pendentes.append((i, titulo_final, path_video_completo))

                    if not arquivos_pendentes:
                        continue
                    
                    print(f"    📂 {mod_nome}: {len(arquivos_pendentes)} vídeos novos para subir...")

                    # --- LOOP DE UPLOAD ---
                    for ordem, titulo, path_arq in arquivos_pendentes:
                        # Verifica link placeholder (Sincronia com Admin)
                        link_atual = await asyncio.to_thread(self.check_link_atual, modulo, titulo)
                        if "http://uploading" in link_atual:
                            print(f"      ⏳ {titulo} [Sendo processado pelo Admin - Pulando]")
                            continue
                        if "tg://" in link_atual:
                            print(f"      ⏭️ {titulo} [Já existe]")
                            continue

                        # Reserva vaga no banco
                        await asyncio.to_thread(self.reservar_vaga, modulo, titulo, ordem, path_arq)

                        print(f"      ☁️ [SUBINDO] {titulo} ...")
                        
                        try:
                            legenda = f"#{area_nome} > {curso_nome}\n📂 {mod_nome}\n🎬 {titulo}"
                            
                            async def progress(current, total):
                                pct = current * 100 / total
                                print(f"\r        Progresso: {pct:.1f}%", end="")

                            # Reconexão Automática
                            if not client.is_connected():
                                await client.connect()

                            msg = await client.send_file(
                                CHANNEL_ID, 
                                path_arq, 
                                caption=legenda, 
                                progress_callback=progress
                            )
                            link_tg = f"tg://{CHANNEL_ID}/{msg.id}"
                            print(" ✅ OK!")

                            # Atualiza com link final
                            await asyncio.to_thread(
                                self.salvar_link_final, 
                                modulo, titulo, link_tg
                            )
                            
                        except Exception as e:
                            print(f"\n      ❌ ERRO: {e}")
                            # Libera a vaga em caso de erro
                            await asyncio.to_thread(self.liberar_vaga, modulo, titulo)

        print("\n🏁 Processo finalizado!")

    # --- BANCO DE DADOS BLINDADO ---
    # Adicionamos close_old_connections() em TODAS as chamadas de banco

    def get_or_create_area(self, nome):
        close_old_connections() # <--- Reset de Conexão
        obj, _ = AreaConhecimento.objects.get_or_create(nome=nome)
        return obj

    def get_or_create_esp(self, nome, area):
        close_old_connections()
        obj, _ = Especialidade.objects.get_or_create(nome=nome, area=area)
        return obj

    def get_or_create_curso(self, titulo, especialidade):
        close_old_connections()
        obj, _ = Curso.objects.get_or_create(titulo=titulo, especialidade=especialidade)
        return obj
    
    def get_or_create_modulo(self, titulo, curso, ordem):
        close_old_connections()
        obj, _ = ModuloCurso.objects.get_or_create(titulo=titulo, curso=curso, defaults={'ordem': ordem})
        return obj

    def get_titulos_existentes(self, modulo):
        close_old_connections()
        return list(Aula.objects.filter(modulo=modulo).values_list('titulo', flat=True))

    def check_link_atual(self, modulo, titulo):
        close_old_connections()
        aula = Aula.objects.filter(modulo=modulo, titulo=titulo).first()
        if aula and aula.video_link:
            return aula.video_link
        return ""

    def reservar_vaga(self, modulo, titulo, ordem, path_arq):
        close_old_connections()
        caminho_relativo = path_arq.split('catalogo')[-1].replace('\\', '/') if 'catalogo' in path_arq else ''
        Aula.objects.update_or_create(
            modulo=modulo, 
            titulo=titulo, 
            defaults={
                'ordem': ordem, 
                'video_link': 'http://uploading', # Trava para o Admin não pegar
                'video_arquivo': caminho_relativo
            }
        )

    def salvar_link_final(self, modulo, titulo, link_tg):
        close_old_connections()
        aula = Aula.objects.get(modulo=modulo, titulo=titulo)
        aula.video_link = link_tg
        aula.save()

    def liberar_vaga(self, modulo, titulo):
        close_old_connections()
        try:
            aula = Aula.objects.get(modulo=modulo, titulo=titulo)
            if aula.video_link == 'http://uploading':
                aula.video_link = ''
                aula.save()
        except: pass