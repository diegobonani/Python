from django.core.management.base import BaseCommand
from usuarios.models import Perfil
from estudos.services.sed_scraper import puxar_boletim_publico_sed

class Command(BaseCommand):
    help = 'Automação de Boletim Escolar (SED - Consulta Pública)'

    def handle(self, *args, **kwargs):
        # 1. Filtra alunos aptos (Estudando + RA + Data Nascimento)
        alunos = Perfil.objects.filter(
            esta_estudando=True, 
            ra_numero__isnull=False,
            data_nascimento__isnull=False
        )
        
        if not alunos.exists():
            self.stdout.write(self.style.WARNING("Nenhum aluno com RA e Data de Nascimento encontrados."))
            self.stdout.write("Dica: Cadastre esses dados no Admin > Usuários > Perfil")
            return

        self.stdout.write(self.style.NOTICE(f"--- Iniciando Robô SED para {alunos.count()} aluno(s) ---"))

        for aluno in alunos:
            self.stdout.write(f"\nIniciando sessão para: {aluno.nome_completo}")
            
            # Chama o robô
            sucesso, msg = puxar_boletim_publico_sed(aluno)
            
            if sucesso:
                self.stdout.write(self.style.SUCCESS(f"✔ SUCESSO: {msg}"))
            else:
                self.stdout.write(self.style.ERROR(f"✖ FALHA: {msg}"))
                
        self.stdout.write(self.style.SUCCESS("\n--- Processo Finalizado ---"))