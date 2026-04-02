from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from usuarios.models import UsuarioLegado, Perfil

class Command(BaseCommand):
    help = 'Sincroniza os usuários da tabela legada "usuarios" para o sistema de autenticação e perfis do Django.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Iniciando a sincronização de usuários legados...'))
        
        # 1. Lê todos os usuários da sua tabela original 'usuarios'
        try:
            legacy_users = UsuarioLegado.objects.all()
            if not legacy_users.exists():
                self.stdout.write(self.style.WARNING("Nenhum usuário encontrado na tabela legada 'usuarios'. Nada a fazer."))
                return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro ao ler a tabela legada 'usuarios': {e}"))
            self.stdout.write(self.style.WARNING("Verifique se o modelo 'UsuarioLegado' em 'usuarios/models.py' está correto e aponta para a tabela 'usuarios'."))
            return

        # 2. Itera sobre cada usuário antigo
        for legacy_user in legacy_users:
            # 3. Cria ou busca o usuário no sistema do Django (tabela auth_user)
            user, created = User.objects.get_or_create(
                username=legacy_user.nome_usuario,
            )

            if created:
                # Define uma senha "inválida" no Django, pois nosso backend customizado
                # continuará verificando a senha em texto puro da tabela antiga.
                user.set_unusable_password()
                user.save()
                self.stdout.write(self.style.SUCCESS(f'>> Usuário Django "{user.username}" criado.'))
            else:
                self.stdout.write(f'-- Usuário Django "{user.username}" já existia. Verificando perfil...')

            # 4. Cria ou atualiza o Perfil associado, garantindo que o TIPO esteja correto
            perfil, perfil_created = Perfil.objects.update_or_create(
                usuario=user,
                defaults={
                    'nome_completo': legacy_user.nome_usuario, # Pode ser ajustado para pegar de outra tabela se necessário
                    'tipo': legacy_user.tipo
                }
            )

            if perfil_created:
                self.stdout.write(self.style.SUCCESS(f'   -> Perfil para "{user.username}" criado com o tipo "{perfil.tipo}".'))
            else:
                self.stdout.write(f'   -> Perfil para "{user.username}" atualizado para o tipo "{perfil.tipo}".')
                
        self.stdout.write(self.style.SUCCESS('\nSincronização concluída com sucesso!'))