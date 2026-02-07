import asyncio
from pyrogram import Client

# Suas credenciais (já configuradas)
API_ID = 36604823
API_HASH = '2787b098e6a8caf60fa6e460a1dd24e5'

app = Client("minha_sessao_streamer", api_id=API_ID, api_hash=API_HASH)

async def main():
    print("🔄 Buscando seus canais e grupos...")
    async with app:
        # Lista todos os diálogos (Canais, Grupos, Conversas)
        async for dialog in app.get_dialogs():
            # Filtra para mostrar apenas Canais ou Grupos
            if str(dialog.chat.type) in ["ChatType.CHANNEL", "ChatType.SUPERGROUP", "ChatType.GROUP"]:
                print(f"Nome: {dialog.chat.title} | ID: {dialog.chat.id}")

if __name__ == '__main__':
    app.run(main())