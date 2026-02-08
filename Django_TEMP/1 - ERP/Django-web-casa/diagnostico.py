import asyncio
from telethon import TelegramClient

# SUAS CREDENCIAIS
API_ID = 36604823
API_HASH = '2787b098e6a8caf60fa6e460a1dd24e5'

async def main():
    print("🔌 Conectando...")
    # Usa a mesma sessão do uploader para ver o que ele vê
    async with TelegramClient('sessao_uploader', API_ID, API_HASH) as client:
        print("✅ Conectado! Buscando lista de canais...")
        print("-" * 60)
        print(f"{'ID':<20} | {'NOME DO CANAL'}")
        print("-" * 60)
        
        # Lista todos os diálogos (canais, grupos, conversas)
        async for dialog in client.iter_dialogs():
            if dialog.is_channel or dialog.is_group:
                print(f"{dialog.id:<20} | {dialog.title}")
        
        print("-" * 60)
        print("Fim da lista.")

if __name__ == '__main__':
    # Fix para Windows
    if asyncio.get_event_loop_policy().__class__.__name__ == 'WindowsProactorEventLoopPolicy':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    asyncio.run(main())