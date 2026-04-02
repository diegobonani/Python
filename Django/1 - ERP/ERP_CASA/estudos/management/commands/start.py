import os
import sys
import subprocess
import time
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Inicia o Streamer e o Django com trava de segurança para login'

    def handle(self, *args, **kwargs):
        python_cmd = sys.executable

        print("==================================================")
        print("🚀 INICIANDO SISTEMA HÍBRIDO")
        print("==================================================")
        print("ℹ️  IGNORE os avisos 'GLib-GIO-WARNING' abaixo.")
        print("ℹ️  Eles são apenas ruído do Windows.")
        print("==================================================")

        try:
            # 1. Inicia o Streamer
            print("🔌 Ligando Streamer (Motor de Vídeo)...")
            processo_streamer = subprocess.Popen([python_cmd, 'streamer_telethon.py'])
            
            # Dá um tempo para o streamer cuspir os logs iniciais
            time.sleep(2) 
            
            print("\n" + "="*60)
            print("🔐  ÁREA DE LOGIN E VERIFICAÇÃO")
            print("="*60)
            print("1. Se o Streamer pediu telefone/código: DIGITE AGORA.")
            print("   (Se você digitar e nada acontecer, digite de novo)")
            print("\n2. Quando aparecer 'TURBO' ou 'Conectado', venha aqui em baixo.")
            print("="*60)
            
            # 2. LOOP DE SEGURANÇA
            # Enquanto você não digitar 'ok', ele não liga o site.
            # Isso impede que o 'Enter' do telefone dispare o site sem querer.
            while True:
                user_input = input("👉 Para ligar o Site, digite 'ok' e dê Enter: ").strip().lower()
                
                if user_input == 'ok':
                    break
                else:
                    print(f"   (Você digitou '{user_input}'. O sistema ignorou para proteger o login.)")
                    print("   Termine de logar no Telegram acima e depois digite 'ok'.\n")
            
            print("\n🌍 Ligando Site (Django) na porta 8000...")
            print("--------------------------------------------------")
            
            processo_django = subprocess.Popen([python_cmd, 'manage.py', 'runserver'])

            # Monitoramento
            while True:
                time.sleep(1)
                if processo_streamer.poll() is not None:
                    print("\n❌ O Streamer fechou inesperadamente!")
                    break
                if processo_django.poll() is not None:
                    print("\n❌ O Django fechou inesperadamente!")
                    break

        except KeyboardInterrupt:
            print("\n\n🛑 Parando serviços...")
            
        finally:
            if 'processo_streamer' in locals():
                processo_streamer.terminate()
            if 'processo_django' in locals():
                processo_django.terminate()
            
            print("✅ Tudo desligado.")