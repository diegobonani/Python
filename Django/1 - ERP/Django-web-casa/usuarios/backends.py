from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from .models import UsuarioLegado, Perfil

class LegacyUserBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None):
        """
        Este método é chamado quando o usuário tenta fazer login.
        """
        try:
            # 1. Procura o usuário na tabela legada 'usuarios'
            legacy_user = UsuarioLegado.objects.get(nome_usuario=username)
            
            # 2. Compara a senha em TEXTO PURO (inseguro!)
            if legacy_user.senha == password:
                
                # 3. Se a senha bate, verifica se já existe um usuário correspondente no Django
                try:
                    user = User.objects.get(username=username)
                except User.DoesNotExist:
                    # Se não existe, cria um novo usuário no sistema do Django (auth_user)
                    user = User(username=legacy_user.nome_usuario)
                    # Define uma senha inutilizável, pois a verificação será sempre neste backend
                    user.set_unusable_password() 
                    user.save()

                # 4. Garante que o Perfil do usuário está sincronizado
                Perfil.objects.update_or_create(
                    usuario=user,
                    defaults={
                        'nome_completo': user.username, # Pode buscar de 'usuarios_dados_pessoais' se quiser
                        'tipo': legacy_user.tipo
                    }
                )
                
                return user # Retorna o usuário do Django para a sessão
            
            return None # Senha incorreta

        except UsuarioLegado.DoesNotExist:
            return None # Usuário não encontrado na tabela legada


    def get_user(self, user_id):
        """
        Este método é usado pelo Django para obter o objeto do usuário da sessão.
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None