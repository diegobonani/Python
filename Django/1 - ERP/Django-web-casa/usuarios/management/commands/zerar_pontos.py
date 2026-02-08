from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import User
from usuarios.models import Perfil, HistoricoResetPontos
from django.db.models import Sum

class Command(BaseCommand):
    help = 'Zera o saldo de pontos de todos os usuários comuns e gera log.'

    def handle(self, *args, **options):
        self.stdout.write("Iniciando reset de pontos...")
        
        # Filtra usuários comuns (Filhos) que têm pontos > 0
        perfis = Perfil.objects.filter(
            usuario__is_superuser=False,
            usuario__is_staff=False,
            saldo_pontos__gt=0  # Só zera quem tem pontos
        )
        
        count = perfis.count()
        total_pontos = perfis.aggregate(Sum('saldo_pontos'))['saldo_pontos__sum'] or 0

        if count == 0:
            self.stdout.write(self.style.WARNING("Nenhum saldo para zerar."))
            return

        try:
            with transaction.atomic():
                # 1. Zera os pontos
                perfis.update(saldo_pontos=0)
                
                # 2. Cria o Log (Sem usuário = Automático)
                HistoricoResetPontos.objects.create(
                    realizado_por=None, 
                    qtd_usuarios_afetados=count,
                    total_pontos_removidos=total_pontos,
                    observacao="Reset mensal automático."
                )

            self.stdout.write(self.style.SUCCESS(f"Sucesso! {total_pontos} pontos removidos de {count} usuários."))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro: {str(e)}"))