import os
import re
import socket
import asyncio
import mysql.connector
from quart import Quart, Response, request
from telethon import TelegramClient
from werkzeug.http import parse_range_header
from hypercorn.asyncio import serve
from hypercorn.config import Config

# --- CONFIGURAÇÕES ---
API_ID = 36604823
API_HASH = '2787b098e6a8caf60fa6e460a1dd24e5'
CHANNEL_ID = -1003842800000 
CAMINHO_BIBLIOTECA_STRM = r'C:\Cursos_Jellyfin_Links'
PORTA_STREAMER = 8888 

# Trocamos Flask por Quart
app = Quart(__name__)
client = TelegramClient('sessao_quart_v1', API_ID, API_HASH)

def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except: return '127.0.0.1'

# --- STREAMING ENGINE (ASSÍNCRONO NATIVO) ---
@app.route('/video/<msg_id>')
async def stream_video(msg_id):
    print(f"📥 [REQUEST] Aula ID: {msg_id}")
    
    try:
        # No Quart, usamos await diretamente sem problemas de loop
        message = await client.get_messages(CHANNEL_ID, ids=int(msg_id))
        
        if not message or not message.media:
            return "Vídeo não encontrado", 404

        file_size = message.file.size
        range_header = request.headers.get('Range')

        async def generate(offset=0, limit=None):
            # Iterador assíncrono do Telethon
            async for chunk in client.iter_download(message.media, offset=offset, limit=limit):
                yield chunk
        
        if range_header:
            ranges = parse_range_header(range_header)
            start, end = ranges.ranges[0][0], (ranges.ranges[0][1] or file_size - 1)
            length = end - start + 1
            
            print(f"⏩ Enviando pedaço: {start} até {end}")
            resp = Response(generate(offset=start, limit=length), 206, mimetype='video/mp4')
            resp.headers['Content-Range'] = f'bytes {start}-{end}/{file_size}'
            resp.headers['Content-Length'] = str(length)
        else:
            print(f"▶️ Enviando vídeo completo")
            resp = Response(generate(), mimetype='video/mp4')
            resp.headers['Content-Length'] = str(file_size)

        resp.headers['Accept-Ranges'] = 'bytes'
        return resp

    except Exception as e:
        print(f"💥 [ERRO]: {e}")
        return str(e), 500

# --- INICIALIZAÇÃO ---
async def main():
    os.makedirs(CAMINHO_BIBLIOTECA_STRM, exist_ok=True)
    
    print("\n🔐 Conectando ao Telegram...")
    await client.start()
    print("✅ Telegram Conectado!")

    config = Config()
    config.bind = [f"0.0.0.0:{PORTA_STREAMER}"]
    
    print(f"\n🚀 SERVIDOR ONLINE: http://{get_ip()}:{PORTA_STREAMER}")
    print("Teste no VLC do PC antes de ir para a TV!")
    
    # Roda o servidor Quart dentro do mesmo loop do Telegram
    await serve(app, config)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDesligando...")