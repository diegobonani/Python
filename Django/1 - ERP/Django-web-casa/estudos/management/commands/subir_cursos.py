import os
import asyncio
import re
from django.core.management.base import BaseCommand
from telethon import TelegramClient
from django.conf import settings
from estudos.models import AreaConhecimento, Especialidade, Curso, ModuloCurso, Aula

# ==============================================================================
# CONFIGURAÇÕES
# ==============================================================================
API_ID = 36604823
API_HASH = '2787b098e6a8caf60fa6e460a1dd24e5'

# ID do Canal de Cursos (Confirme se é este mesmo)
CHANNEL_ID = -1003842800000 

# Caminho Raiz dos Cursos
PASTA_RAIZ = r"C:\Users\DIEGOBONANI\OneDrive\Desktop\Django-web-casa\media\catalogo"

client = TelegramClient('sessao_uploader', API_ID, API_HASH)

class Command(BaseCommand):
    help = 'Robô de Cursos com Sistema de Retomada Inteligente (Resume)'

    def handle(self, *args, **kwargs):
        if not os.path.exists(PASTA_RAIZ):
            self.stdout.write(self.style.ERROR(f"Pasta não encontrada: {PASTA_RAIZ}"))
            return
        
        # Ajuste para Windows
        if asyncio.get_event_loop_policy().__class__.__name__ == 'WindowsProactorEventLoopPolicy':
             asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        print(f"🚀 INICIANDO ROBÔ DE CURSOS (SISTEMA ANTI-DUPLICAÇÃO ATIVO)")
        print(f"📂 Lendo de: {PASTA_RAIZ}")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.processar_pastas())
        except KeyboardInterrupt:
            print("\n🛑 Processo pausado pelo usuário.")

    def natural_sort_key(self, s):
        # Ordena 1, 2, 10 corretamente
        return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]

    async def processar_pastas(self):
        print("🔌 Conectando ao Telegram...")
        await client.start()
        
        await client.get_dialogs()
        try:
            canal_alvo = await client.get_entity(CHANNEL_ID)
            print(f"✅ Canal Conectado: {canal_alvo.title}")
        except Exception as e:
            print(f"❌ Erro ao achar canal {CHANNEL_ID}: {e}")
            return

        print("\n📂 Iniciando varredura geral...")

        # 1. ÁREA (TI, RH, MKT...)
        for area_nome in sorted(os.listdir(PASTA_RAIZ)):
            path_area = os.path.join(PASTA_RAIZ, area_nome)
            if not os.path.isdir(path_area): continue
            
            # Ignora pastas de sistema
            if area_nome in ['uploads_gerais', 'capas', 'System Volume Information', 'KIDS']: continue

            area = await asyncio.to_thread(self.get_or_create_area, area_nome)
            # Cria especialidade Geral automática para manter a hierarquia
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

                    modulo = await asyncio.to_thread(self.get_or_create_modulo, mod_nome, curso, ordem_mod)

                    # 4. AULAS (PREPARAÇÃO DA RETOMADA)
                    arquivos_video = []
                    for root, dirs, files in os.walk(path_mod):
                        for file in files:
                            if file.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.ts')):
                                arquivos_video.append(os.path.join(root, file))
                    
                    # Ordena arquivos matematicamente
                    arquivos_video.sort(key=lambda f: self.natural_sort_key(os.path.basename(f)))
                    
                    if not arquivos_video: continue

                    # --- CHECKLIST DE RETOMADA INTELIGENTE ---
                    # Busca no banco quais episódios JÁ existem neste módulo
                    titulos_existentes = await asyncio.to_thread(self.get_titulos_existentes, modulo)
                    
                    total_arquivos = len(arquivos_video)
                    ja_enviados = 0
                    arquivos_pendentes = []

                    # Verifica um por um na memória
                    for i, path_video_completo in enumerate(arquivos_video, start=1):
                        video_nome_original = os.path.basename(path_video_completo)
                        
                        # Limpeza do Nome e Geração do Título Final
                        nome_base = os.path.splitext(video_nome_original)[0].replace('_', ' ')
                        nome_limpo = re.sub(r'^[\d\.\-\s]+', '', nome_base) or nome_base
                        titulo_final = f"{i:02d}. {nome_limpo}"

                        if titulo_final in titulos_existentes:
                            ja_enviados += 1
                        else:
                            # Adiciona na fila de upload
                            arquivos_pendentes.append((i, titulo_final, path_video_completo))

                    # RELATÓRIO NO TERMINAL
                    if ja_enviados == total_arquivos:
                        # Se já subiu tudo, nem avisa, só pula silenciosamente pra ser rápido
                        # print(f"    ✅ {mod_nome}: Completo.")
                        continue
                    elif ja_enviados > 0:
                        print(f"    🔄 {mod_nome}: {ja_enviados}/{total_arquivos} vídeos prontos. Retomando...")
                    else:
                        print(f"    📂 {mod_nome}: Iniciando upload de {total_arquivos} vídeos...")

                    # --- LOOP DE UPLOAD (APENAS O QUE FALTA) ---
                    for ordem, titulo, path_arq in arquivos_pendentes:
                        print(f"      📤 [SUBINDO] {titulo} ...")
                        
                        try:
                            legenda = f"#{area_nome} > {curso_nome}\n📂 {mod_nome}\n🎬 {titulo}"
                            
                            async def progress(current, total):
                                pct = current * 100 / total
                                print(f"\r         Progresso: {pct:.1f}%", end="")

                            # Upload pro Telegram
                            msg = await client.send_file(
                                canal_alvo, 
                                path_arq, 
                                caption=legenda, 
                                progress_callback=progress
                            )
                            link_tg = f"tg://{CHANNEL_ID}/{msg.id}"
                            print(" ✅ OK!")

                            # Salva no Banco
                            await asyncio.to_thread(
                                self.criar_aula, 
                                modulo, titulo, ordem, link_tg
                            )
                            
                        except Exception as e:
                            print(f"\n      ❌ ERRO: {e}")

        print("\n🏁 Processo finalizado!")

    # --- BANCO DE DADOS ---
    def get_or_create_area(self, nome):
        obj, _ = AreaConhecimento.objects.get_or_create(nome=nome)
        return obj

    def get_or_create_esp(self, nome, area):
        obj, _ = Especialidade.objects.get_or_create(nome=nome, area=area)
        return obj

    def get_or_create_curso(self, titulo, especialidade):
        obj, _ = Curso.objects.get_or_create(titulo=titulo, especialidade=especialidade)
        return obj
    
    def get_or_create_modulo(self, titulo, curso, ordem):
        obj, _ = ModuloCurso.objects.get_or_create(titulo=titulo, curso=curso, defaults={'ordem': ordem})
        return obj

    def get_titulos_existentes(self, modulo):
        # Pega a lista de todos os vídeos desse módulo de uma vez só
        return set(Aula.objects.filter(modulo=modulo).values_list('titulo', flat=True))

    def criar_aula(self, modulo, titulo, ordem, link_tg):
        Aula.objects.create(
            modulo=modulo, 
            titulo=titulo, 
            ordem=ordem, 
            video_link=link_tg
        )