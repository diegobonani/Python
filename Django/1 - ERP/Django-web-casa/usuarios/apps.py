# Em usuarios/apps.py

from django.apps import AppConfig

class UsuariosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'usuarios'

    def ready(self):
        # Importa os signals para que eles sejam registrados
        import usuarios.signals