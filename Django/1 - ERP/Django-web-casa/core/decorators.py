# Em core/decorators.py (ou onde preferir)

from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied

def admin_required(view_func):
    """
    Decorator que verifica se o usuário é Super User OU pertence ao 
    grupo 'Administradores'.
    """
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        if request.user.is_authenticated and request.user.groups.filter(name='Administradores').exists():
            return view_func(request, *args, **kwargs)
        
        # Se não for nenhum dos dois, nega o acesso
        raise PermissionDenied
    return _wrapped_view


def superuser_required(view_func):
    """
    Decorator que verifica se o usuário é APENAS Super User.
    """
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# Você também pode usar a versão integrada do Django:
# from django.contrib.admin.views.decorators import staff_member_required
# O @staff_member_required é quase a mesma coisa que @superuser_required
# se você configurar que 'is_staff' é só para superusers.