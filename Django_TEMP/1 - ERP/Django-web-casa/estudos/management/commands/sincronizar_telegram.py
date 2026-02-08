import asyncio
import re
import os
from django.core.management.base import BaseCommand
from estudos.models import AreaConhecimento, Especialidade, Curso, ModuloCurso, Aula
from pyrogram import Client
from pyrogram.enums import MessageMediaType

# ==========================================
# SUAS CREDENCIAIS
# ==========================================
API_ID = 36604823
API_HASH = '2787b098e6a8caf60fa6e460a1dd24e5'

# --- IMPORTANTE: SUBSTITUA ISSO PELO ID DO SEU CANAL ---
# Dica: Use o streamer.py para descobrir ou copie o link da msg (-100...)
CHAT_ID = -1003842800000

class Command(BaseCommand):
    help = 'Lê o canal do Telegram e cria os cursos no Django'

    def limpar_nome(self, texto):
        """ Remove números (001 - ) e extensão (.mp4) do nome """
        if not texto: return "Aula Sem Nome"
        
        # Remove a extensão (ex: .mp4)
        texto = texto.rsplit('.', 1)[0]
        
        # Regex: Remove dígitos, traços, pontos e espaços do COMEÇO
        # Ex: "001 - Aula.mp4" vira "Aula"
        texto_limpo = re.sub(r'^[\d\s\.\-_]+', '', texto)
        
        return texto_limpo.strip() if texto_limpo.strip() else texto

    async def sync_worker(self):
        print("🔌 Conectando ao Telegram...")
        
        # Usa a mesma sessão do streamer para não pedir código de novo
        async with Client("minha_sessao_streamer", api_id=API_ID, api_hash=API_HASH) as app:
            
            print(f"📂 Lendo canal {CHAT_ID}...")
            
            # Cria/Pega a Área Padrão
            area, _ = await asyncio.to_thread(AreaConhecimento.objects.get_or_create, nome="Cursos Telegram")
            
            count_novos = 0
            count_total = 0

            # Itera sobre todas as mensagens do canal (do mais antigo pro mais novo)
            # Para inverter a ordem de leitura, inverta a lógica se necessário, mas o padrão é histórico.
            async for msg in app.get_chat_history(CHAT_ID):
                
                # Só nos interessa se tiver VÍDEO
                if msg.media == MessageMediaType.VIDEO:
                    count_total += 1
                    
                    # 1. DEFINIR NOME DO CURSO E MÓDULO
                    # Prioridade: Legenda (Caption) > Padrão
                    nome_curso = "Importados Telegram"
                    nome_modulo = "Geral"
                    
                    if msg.caption:
                        # Espera: "Nome do Curso | Nome do Módulo"
                        partes = msg.caption.split('|')
                        if len(partes) >= 1: nome_curso = partes[0].strip()
                        if len(partes) >= 2: nome_modulo = partes[1].strip()
                    
                    # 2. LIMPAR NOME DA AULA
                    nome_arquivo = msg.video.file_name or f"Aula {msg.id}"
                    titulo_aula = self.limpar_nome(nome_arquivo)

                    # 3. LINK MÁGICO (O Segredo do Streaming)
                    # Formato: tg://ID_CANAL/ID_MENSAGEM
                    # Isso diz pro Django onde buscar o vídeo depois
                    link_tg = f"tg://{CHAT_ID}/{msg.id}"

                    # --- OPERAÇÕES DE BANCO DE DADOS (SYNC WRAPPED IN ASYNC) ---
                    
                    # Verifica se essa aula já existe para não duplicar
                    exists = await asyncio.to_thread(
                        Aula.objects.filter(video_link=link_tg).exists
                    )
                    
                    if not exists:
                        print(f"🆕 Processando: {titulo_aula} ({nome_curso})")

                        # Cria Especialidade/Curso
                        espec, _ = await asyncio.to_thread(Especialidade.objects.get_or_create, nome=nome_curso, defaults={'area': area})
                        curso, _ = await asyncio.to_thread(Curso.objects.get_or_create, titulo=nome_curso, defaults={'especialidade': espec})
                        
                        # Tenta extrair número do módulo se houver (Ex: "Módulo 1")
                        ordem_mod = 99
                        match_mod = re.search(r'(\d+)', nome_modulo)
                        if match_mod: ordem_mod = int(match_mod.group(1))

                        modulo, _ = await asyncio.to_thread(ModuloCurso.objects.get_or_create, curso=curso, titulo=nome_modulo, defaults={'ordem': ordem_mod})
                        
                        # Define a ordem da aula (sequencial dentro do módulo)
                        qtd_aulas = await asyncio.to_thread(Aula.objects.filter(modulo=modulo).count)
                        
                        # Salva a Aula
                        await asyncio.to_thread(
                            Aula.objects.create,
                            modulo=modulo,
                            titulo=titulo_aula,
                            ordem=qtd_aulas + 1,
                            video_link=link_tg,
                            video_arquivo=None, # Importante: Sem arquivo local
                            duracao="" # Pode implementar calculo de tempo depois
                        )
                        count_novos += 1
                    else:
                        # print(f"   (Ignorado) Já existe: {titulo_aula}")
                        pass

            print(f"\n✅ FINALIZADO!")
            print(f"   - Vídeos encontrados no canal: {count_total}")
            print(f"   - Novos vídeos cadastrados: {count_novos}")

    def handle(self, *args, **options):
        # Configura o loop assíncrono do Django
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.sync_worker())
        except KeyboardInterrupt:
            print("Cancelado pelo usuário.")
        finally:
            loop.close()