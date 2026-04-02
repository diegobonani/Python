from telethon import TelegramClient
import asyncio

API_ID = 36604823
API_HASH = '2787b098e6a8caf60fa6e460a1dd24e5'
CHANNEL_ID = -1003842800000 
MSG_ID = 10  # ID de uma aula que você sabe que existe

async def test():
    client = TelegramClient('sessao_jellyfin', API_ID, API_HASH)
    await client.start()
    
    print("✅ Conectado ao Telegram!")
    
    try:
        # Tenta buscar a mensagem
        msg = await client.get_messages(CHANNEL_ID, ids=MSG_ID)
        
        if msg and msg.media:
            print(f"🎬 Vídeo encontrado: {msg.file.name if msg.file.name else 'Sem nome'}")
            print(f"📦 Tamanho: {msg.file.size / (1024*1024):.2f} MB")
            
            # Tenta baixar apenas 1MB para testar a velocidade
            print("⏳ Testando download do primeiro pedaço...")
            async for chunk in client.iter_download(msg.media, limit=1024*1024):
                if chunk:
                    print("🚀 Sucesso! Recebi dados do Telegram.")
                    break
        else:
            print("❌ Mensagem encontrada, mas não contém mídia ou o ID está incorreto.")
            
    except Exception as e:
        print(f"❌ Erro ao acessar canal/mensagem: {e}")
    finally:
        await client.disconnect()

asyncio.run(test())