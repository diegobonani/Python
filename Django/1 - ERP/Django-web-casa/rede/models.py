from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import RegexValidator

class Dispositivo(models.Model):
    TIPO_CHOICES = [
        ('CELULAR', 'Celular/Tablet'),
        ('TV', 'Smart TV'),
        ('NOTEBOOK', 'Notebook/PC'),
        ('GAME', 'Console (Videogame)'),
        ('IOT', 'Casa Inteligente (Alexa/Lâmpada)'),
        ('OUTRO', 'Outro'),
    ]

    STATUS_CHOICES = [
        ('LIBERADO', 'Liberado'),
        ('BLOQUEADO', 'Bloqueado Manualmente'),
        ('CASTIGO', 'Em Castigo (Tempo)'),
    ]

    # Dono do dispositivo (Pai, Mãe, Filho...)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="dispositivos_rede",
        verbose_name="Dono do Dispositivo"
    )
    
    nome = models.CharField(max_length=50, help_text="Ex: iPhone do Diego, TV Sala")
    mac_address = models.CharField(
        max_length=17, 
        unique=True, 
        verbose_name="Endereço MAC",
        validators=[RegexValidator(regex=r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$', message="Formato inválido (XX:XX:XX:XX:XX:XX)")],
        help_text="Formato: 00:1A:2B:3C:4D:5E"
    )
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default='CELULAR')
    
    # Controle de Acesso
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='LIBERADO')
    
    # Lógica de Castigo / Tempo
    castigo_ate = models.DateTimeField(null=True, blank=True, verbose_name="Bloqueado até")
    
    # Monitoramento (Isso precisaria de um script externo atualizando, mas vamos deixar a estrutura)
    ultimo_visto = models.DateTimeField(null=True, blank=True, verbose_name="Última Conexão")
    tempo_uso_hoje = models.DurationField(default=timezone.timedelta(0), verbose_name="Tempo de Uso Hoje")

    class Meta:
        verbose_name = "Dispositivo de Rede"
        verbose_name_plural = "Dispositivos de Rede"

    def __str__(self):
        return f"{self.nome} ({self.usuario.username})"

    @property
    def esta_bloqueado(self):
        """Verifica se está bloqueado agora (manual ou castigo)"""
        if self.status == 'BLOQUEADO':
            return True
        if self.status == 'CASTIGO' and self.castigo_ate and self.castigo_ate > timezone.now():
            return True
        return False