from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.conf import settings 

class Veiculo(models.Model):
    proprietario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='veiculos_pertencentes')
    autorizado_a_usar = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='veiculos_autorizados', blank=True)
    
    nome = models.CharField(max_length=100)
    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=50)
    ano = models.PositiveIntegerField()
    placa = models.CharField(max_length=10, unique=True, blank=True, null=True)
    km_atual = models.PositiveIntegerField(default=0, verbose_name="Odômetro Atual")

    # Consumo
    consumo_cidade_gasolina = models.DecimalField(max_digits=5, decimal_places=2, default=10.0)
    consumo_estrada_gasolina = models.DecimalField(max_digits=5, decimal_places=2, default=14.0)
    consumo_cidade_etanol = models.DecimalField(max_digits=5, decimal_places=2, default=7.0)
    consumo_estrada_etanol = models.DecimalField(max_digits=5, decimal_places=2, default=10.0)

    def __str__(self):
        return f"{self.modelo} - {self.placa}"

class Servico(models.Model):
    """Catálogo de Manutenções (Ex: Troca de Óleo)"""
    veiculo = models.ForeignKey(Veiculo, on_delete=models.CASCADE, related_name="servicos")
    nome = models.CharField(max_length=200)
    intervalo_km = models.PositiveIntegerField(null=True, blank=True)
    intervalo_dias = models.PositiveIntegerField(null=True, blank=True)
    ultima_km = models.PositiveIntegerField(default=0)
    ultima_data = models.DateField(default=timezone.now)

    def __str__(self): return self.nome

    @property
    def proxima_data_vencimento(self):
        return self.ultima_data + timedelta(days=self.intervalo_dias) if self.intervalo_dias else None

    @property
    def proxima_km_vencimento(self):
        return self.ultima_km + self.intervalo_km if self.intervalo_km else None

# --- NOVO: MUDAMOS A MANUTENÇÃO PARA CÁ ---
class Manutencao(models.Model):
    """
    Registra serviços mecânicos. 
    GATILHO: Cria despesa financeira e atualiza KM.
    """
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    veiculo = models.ForeignKey(Veiculo, on_delete=models.CASCADE, related_name='manutencoes')
    
    servico_realizado = models.ForeignKey(Servico, on_delete=models.SET_NULL, null=True, blank=True)
    descricao = models.CharField(max_length=255, verbose_name="Descrição Detalhada")
    data_servico = models.DateField(default=timezone.now)
    
    km_odometro = models.PositiveIntegerField(verbose_name="Odômetro no Serviço (KM)")
    custo_total = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Custo Total (R$)")
    
    # Vínculo Financeiro
    lancamento_financeiro = models.OneToOneField(
        'financas.Financa', 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='manutencao_origem'
    )

    class Meta:
        verbose_name = "Manutenção"
        verbose_name_plural = "Manutenções"
        ordering = ['-data_servico']

    def __str__(self):
        return f"Manutenção {self.veiculo.modelo} - {self.descricao}"