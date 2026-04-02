from django.core.management.base import BaseCommand
from usuarios.models import Perfil
from estudos.services.sed_scraper import puxar_boletim_sed

class Command(BaseCommand):
    help = 'Sincroniza boletins da SED para alunos com RA cadastrado'

    def handle(self, *args, **kwargs):
        alunos = Perfil.objects.filter(esta_estudando=True).exclude(ra_numero__isnull=True)
        
        for aluno in alunos:
            self.stdout.write(f"Sincronizando: {aluno.nome_completo}")
            sucesso = puxar_boletim_sed(
                aluno.ra_numero, 
                aluno.ra_digito, 
                aluno.ra_uf, 
                aluno.senha_sed
            )
            if sucesso:
                self.stdout.write(self.style.SUCCESS(f"OK: {aluno.nome_completo}"))
            else:
                self.stdout.write(self.style.ERROR(f"FALHA: {aluno.nome_completo}"))