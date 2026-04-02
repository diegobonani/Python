from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django.db import transaction

from usuarios.models import UsuarioLegado  # ajuste se o nome do app for diferente


User = get_user_model()


class Command(BaseCommand):
    help = "Migra os papéis da tabela 'usuarios' (legado) para Groups do Django (ADMIN_FAMILIA / LEITURA)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Executa sem salvar alterações no banco."
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        self.stdout.write(self.style.NOTICE("=== INICIANDO MIGRAÇÃO DE GRUPOS ==="))

        # Criar ou obter grupos
        grupo_admin, _ = Group.objects.get_or_create(name="ADMIN_FAMILIA")
        grupo_leitura, _ = Group.objects.get_or_create(name="LEITURA")

        total = 0
        migrados = 0
        faltando_auth = 0
        tipo_desconhecido = 0

        for legado in UsuarioLegado.objects.all().order_by("id"):
            total += 1

            username = (legado.nome_usuario or "").strip()
            tipo = (legado.tipo or "").strip().lower()

            if not username:
                self.stdout.write(
                    self.style.WARNING(f"[IGNORADO] ID {legado.id} sem username.")
                )
                continue

            try:
                auth_user = User.objects.get(username=username)
            except User.DoesNotExist:
                faltando_auth += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"[SEM auth_user] legado.id={legado.id} username='{username}' tipo='{legado.tipo}'"
                    )
                )
                continue

            # Determinar grupo alvo
            if tipo == "administrador":
                grupo_alvo = grupo_admin
            elif tipo in ("usuário comum", "usuario comum"):
                grupo_alvo = grupo_leitura
            else:
                tipo_desconhecido += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"[TIPO desconhecido] legado.id={legado.id} username='{username}' tipo='{legado.tipo}'"
                    )
                )
                continue

            if dry_run:
                self.stdout.write(
                    f"[DRY-RUN] {username} seria adicionado ao grupo '{grupo_alvo.name}'"
                )
                migrados += 1
            else:
                auth_user.groups.add(grupo_alvo)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[OK] {username} adicionado ao grupo '{grupo_alvo.name}'"
                    )
                )
                migrados += 1

        self.stdout.write("\n=== RESUMO ===")
        self.stdout.write(f"Total analisados: {total}")
        self.stdout.write(f"Migrados/Confirmados: {migrados}")
        self.stdout.write(f"Sem auth_user correspondente: {faltando_auth}")
        self.stdout.write(f"Tipos desconhecidos: {tipo_desconhecido}")

        if dry_run:
            self.stdout.write(
                self.style.WARNING("\nDry-run finalizado. Nenhuma alteração foi salva.")
            )
            # Força rollback intencional
            raise transaction.TransactionManagementError(
                "Dry-run concluído com rollback."
            )

        self.stdout.write(self.style.SUCCESS("\nMigração concluída com sucesso!"))
