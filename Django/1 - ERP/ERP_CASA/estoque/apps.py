from django.apps import AppConfig


class EstoqueConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'estoque'

    # Adicione este método
    def ready(self):
        import estoque.signals # Importa nossos sinais para que eles sejam registrados