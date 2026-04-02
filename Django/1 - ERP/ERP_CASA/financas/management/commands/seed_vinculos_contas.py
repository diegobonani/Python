# financas/management/commands/seed_vinculos_contas.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from financas.models import ContaFinanceira, ContaVinculo

User = get_user_model()

class Command(BaseCommand):
    help = "Cria ContaVinculo automaticamente com base nas contas existentes."

    def handle(self, *args, **kwargs):
        created = 0

        contas = ContaFinanceira.objects.all().select_related("usuario")
        for conta in contas:
            # regra:
            # - se conta is_shared, vincula a todos os admins (ou a um conjunto específico)
            # - se não for shared e tiver usuario, vincula ao usuario dono
            if conta.is_shared:
                # você pode trocar este filtro por um grupo específico (ADMIN_FAMILIA)
                admins = User.objects.filter(is_staff=True) | User.objects.filter(is_superuser=True)
                admins = admins.distinct()

                for u in admins:
                    _, was_created = ContaVinculo.objects.get_or_create(conta=conta, usuario=u, defaults={"ativa": True})
                    if was_created:
                        created += 1

            else:
                if conta.usuario_id:
                    _, was_created = ContaVinculo.objects.get_or_create(conta=conta, usuario=conta.usuario, defaults={"ativa": True})
                    if was_created:
                        created += 1

        self.stdout.write(self.style.SUCCESS(f"OK. Vinculos criados: {created}"))
