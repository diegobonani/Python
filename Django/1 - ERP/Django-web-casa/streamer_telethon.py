import asyncio
import os
import mimetypes
import sys
from telethon import TelegramClient
from aiohttp import web

# ==========================================
# CONFIGURAÇÕES
# ==========================================
API_ID = 36604823
API_HASH = '2787b098e6a8caf60fa6e460a1dd24e5'

# Verifica Acelerador
try:
    import cryptg
    print("🚀 [TURBO] Biblioteca 'cryptg' ATIVADA!")
except ImportError:
    print("⚠️ [LENTO] 'cryptg' não instalado. Instale com: pip install cryptg")

# Pasta de Cache
CACHE_DIR = os.path.join(os.getcwd(), 'media', 'stream_cache')
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

# Configuração agressiva de conexão
client = TelegramClient(
    'sessao_streamer', 
    API_ID, 
    API_HASH,
    flood_sleep_threshold=0, # Não dorme, tenta de novo
    request_retries=10 # Insiste mais vezes se falhar
)

# Controle de Downloads
active_downloads = {}

async def background_downloader(message, file_path, msg_id):
    """ Baixa com blocos maiores (1MB) para saturar a banda e evitar engasgos """
    print(f"⬇️ [BUFFER] Baixando: {msg_id} (Modo Turbo)")
    try:
        with open(file_path, 'wb') as f:
            # Aumentado para 1MB (1024*1024). 
            # Menos 'pedidos' ao servidor = download mais contínuo.
            async for chunk in client.iter_download(message.media, chunk_size=1024*1024):
                if not chunk: break
                f.write(chunk)
                f.flush()
                os.fsync(f.fileno()) # Força gravar no disco AGORA
        
        print(f"✅ [BUFFER] Completo: {msg_id}")
    except Exception as e:
        print(f"❌ [BUFFER] Erro: {e}")
        if os.path.exists(file_path):
            try: os.remove(file_path)
            except: pass
    finally:
        if msg_id in active_downloads:
            del active_downloads[msg_id]

async def stream_handler(request):
    try:
        # 1. Identificar ID
        str_channel_id = request.match_info['channel_id']
        message_id = int(request.match_info['message_id'])
        
        if str_channel_id.startswith('-100'):
            real_channel_id = int(str_channel_id)
        else:
            real_channel_id = int(f"-100{str_channel_id}")

        filename = f"{real_channel_id}_{message_id}.mp4"
        file_path = os.path.join(CACHE_DIR, filename)

        # 2. Iniciar Download (Se necessário)
        file_total_size = 0
        is_downloading = message_id in active_downloads
        
        if not os.path.exists(file_path) and not is_downloading:
            print(f"⚡ Solicitado vídeo novo...")
            try:
                message = await client.get_messages(real_channel_id, ids=message_id)
                if not message or not message.file:
                     return web.Response(status=404, text="404 Telegram")
                
                file_total_size = message.file.size
                
                # Cria arquivo vazio
                with open(file_path, 'wb') as f: pass
                
                # Dispara Background Task
                active_downloads[message_id] = asyncio.create_task(
                    background_downloader(message, file_path, message_id)
                )
            except Exception as e:
                print(f"Erro Telegram: {e}")
                return web.Response(status=404)
        else:
            # Tamanho Total
            if os.path.exists(file_path) and not is_downloading:
                file_total_size = os.path.getsize(file_path)
            else:
                # Estimativa ou Query rápida
                try:
                    message = await client.get_messages(real_channel_id, ids=message_id)
                    file_total_size = message.file.size
                except:
                    file_total_size = 500 * 1024 * 1024 

        # 3. HTTP Headers
        range_header = request.headers.get('Range')
        offset = 0
        limit = file_total_size - 1

        if range_header:
            try:
                parts = range_header.replace('bytes=', '').split('-')
                offset = int(parts[0])
                if len(parts) > 1 and parts[1]:
                    limit = int(parts[1])
            except: pass

        content_length = limit - offset + 1

        headers = {
            'Content-Type': 'video/mp4',
            'Accept-Ranges': 'bytes',
            'Content-Range': f'bytes {offset}-{limit}/{file_total_size}',
            'Content-Length': str(content_length),
            'Access-Control-Allow-Origin': '*',
        }

        response = web.StreamResponse(status=206, headers=headers)
        await response.prepare(request)

        # 4. Leitura Inteligente com Timeout
        bytes_sent = 0
        timeout_counter = 0 

        with open(file_path, 'rb') as f:
            f.seek(offset)
            
            while bytes_sent < content_length:
                # Lê bloco de 128KB (Buffer de leitura suave)
                chunk = f.read(128 * 1024) 
                
                if not chunk:
                    if message_id in active_downloads:
                        # Espera chegar mais dados
                        await asyncio.sleep(0.1)
                        timeout_counter += 1
                        f.seek(offset + bytes_sent) # Tenta ler de novo o mesmo lugar
                        
                        if timeout_counter > 300: # 30s Timeout
                            print("⚠️ Timeout esperando buffer...")
                            break
                        continue
                    else:
                        break # Fim do arquivo
                
                timeout_counter = 0
                
                if bytes_sent + len(chunk) > content_length:
                    chunk = chunk[:content_length - bytes_sent]
                
                try:
                    await response.write(chunk)
                    # await response.drain() # Descomentar se der engasgo no Chrome
                except:
                    break

                bytes_sent += len(chunk)

        return response

    except Exception as e:
        print(f"❌ Erro Crítico: {e}")
        return web.Response(status=500)

async def start_server():
    print("--------------------------------------------------")
    print("🚀 STREAMER TURBO (1MB CHUNK) INICIADO")
    await client.start()
    print("--------------------------------------------------")
    app = web.Application()
    app.router.add_get('/stream/{channel_id}/{message_id}', stream_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    await asyncio.Event().wait()

if __name__ == '__main__':
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt: pass