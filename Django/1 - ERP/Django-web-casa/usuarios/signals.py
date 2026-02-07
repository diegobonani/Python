# Em: usuarios/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User, Group
from .models import Perfil

@receiver(post_save, sender=Perfil)
def add_user_to_group(sender, instance, created, **kwargs):
    """
    Sincroniza o 'tipo' do Perfil com os Grupos do Django.
    """
    try:
        # Tenta buscar os grupos que você DEVE criar no /admin
        admin_group = Group.objects.get(name='Administradores')
        common_group = Group.objects.get(name='Usuarios_Comuns')
    except Group.DoesNotExist:
        # Se os grupos ainda não existem no banco, 
        # o signal falha silenciosamente para não quebrar o sistema.
        # Lembre-se de criar os grupos no Django Admin!
        print("AVISO: Grupos 'Administradores' ou 'Usuarios_Comuns' não encontrados.")
        return

    # Pega o usuário associado a este perfil
    user = instance.usuario

    # Limpa os grupos antigos para garantir que ele não fique nos dois
    user.groups.remove(admin_group, common_group)

    # Adiciona ao grupo correto baseado no campo 'tipo' do Perfil
    if instance.tipo == 'Administrador':
        user.groups.add(admin_group)
    elif instance.tipo == 'Usuário Comum':
        user.groups.add(common_group)

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Cria um Perfil padrão quando um User do Django é criado.
    (Isso evita erros caso você crie um usuário sem criar um perfil)
    """
    if created:
        # Se o usuário for Superuser, cria o perfil como Administrador
        if instance.is_superuser:
            Perfil.objects.create(usuario=instance, 
                                  nome_completo=instance.username, 
                                  tipo='Administrador')
        else:
            # Para todos os outros, cria como Usuário Comum
            Perfil.objects.create(usuario=instance, 
                                  nome_completo=instance.username, 
                                  tipo='Usuário Comum')