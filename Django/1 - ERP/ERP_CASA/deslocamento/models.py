from django.db import models
from django.conf import settings
from django.db.models import DecimalField
import datetime
# Importação condicional para evitar dependência circular se necessário, 
# mas geralmente o import direto funciona se apps estiverem instalados.
from carro.models import Veiculo 

# Se você já tiver o app financas criado, podemos importar o modelo para usar no ForeignKey
# from financas.models import Lancamento (Faremos isso via string 'financas.Lancamento' para evitar erro)

class LocalizacaoFrequente(models.Model):
    """
    Pontos fixos de interesse do usuário (Casa, Trabalho, etc.) para facilitar a seleção.
    """
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name="localizacoes_deslocamento"
    )
    nome = models.CharField(max_length=100, verbose_name="Nome do Local")
    endereco_texto = models.CharField(max_length=255, verbose_name="Endereço Completo")
    
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta:
        verbose_name = "Localização Frequente"
        verbose_name_plural = "Localizações Frequentes"
        unique_together = ('usuario', 'nome')
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} ({self.usuario.username})"


# --- NOVO MODELO: ABASTECIMENTO (O Gatilho do Sistema) ---
class Abastecimento(models.Model):
    """
    Registra a compra de combustível.
    GATILHOS (Signals):
    1. Atualiza o KM Atual do Veículo.
    2. Cria uma Despesa no App Finanças.
    """
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE
    )
    veiculo = models.ForeignKey(
        Veiculo, 
        on_delete=models.CASCADE, # Se deletar o carro, deleta os abastecimentos
        verbose_name="Veículo"
    )
    data = models.DateField(default=datetime.date.today, verbose_name="Data")
    
    # Dados do Posto
    km_odometro = models.PositiveIntegerField(verbose_name="KM no Odômetro (Painel)", help_text="Valor exato que está no painel na hora do abastecimento")
    litros = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="Litros Abastecidos")
    valor_total = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Valor Total (R$)")
    valor_litro = models.DecimalField(max_digits=6, decimal_places=3, verbose_name="Preço por Litro", blank=True, null=True)
    
    TIPO_COMBUSTIVEL_CHOICES = [
        ('GASOLINA', 'Gasolina Comum'),
        ('GAS_ADIT', 'Gasolina Aditivada'),
        ('ETANOL', 'Etanol'),
        ('DIESEL', 'Diesel'),
        ('GNV', 'GNV'),
    ]
    tipo_combustivel = models.CharField(max_length=10, choices=TIPO_COMBUSTIVEL_CHOICES, default='GASOLINA')
    
    posto = models.CharField(max_length=100, blank=True, null=True, verbose_name="Posto de Gasolina")
    tanque_cheio = models.BooleanField(default=True, verbose_name="Tanque Cheio?")
    
    # VÍNCULO COM FINANÇAS
    # Usamos string 'financas.Lancamento' para evitar erro de importação circular
    lancamento_financeiro = models.OneToOneField(
        'financas.Financa', 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='abastecimento_origem',
        help_text="Vincula este abastecimento a uma saída de dinheiro no caixa."
    )

    def save(self, *args, **kwargs):
        # Calcula valor do litro automaticamente se não informado
        if self.valor_total and self.litros and not self.valor_litro:
            self.valor_litro = self.valor_total / self.litros
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Abastecimento"
        verbose_name_plural = "Abastecimentos"
        ordering = ['-data', '-km_odometro']

    def __str__(self):
        return f"Abastecimento {self.veiculo} - {self.data}"


class DiaDeDeslocamento(models.Model):
    """
    Agrupa todos os trechos (Percursos) de uma viagem de um dia.
    Contém os totais apurados.
    """
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name="dias_deslocamento"
    )
    data = models.DateField(default=datetime.date.today, verbose_name="Data do Deslocamento")
    veiculo = models.ForeignKey(
        Veiculo, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        verbose_name="Veículo Utilizado"
    )
    
    # --- DADOS DE COMBUSTÍVEL E CÁLCULO ---
    
    TIPO_COMBUSTIVEL_CHOICES = [
        ('GASOLINA', 'Gasolina'),
        ('ETANOL', 'Etanol/Álcool'),
    ]
    tipo_combustivel = models.CharField(
        max_length=10, 
        choices=TIPO_COMBUSTIVEL_CHOICES, 
        default='GASOLINA',
        verbose_name="Combustível Usado"
    )
    
    # NOVO: Tipo de Trajeto (para decidir qual consumo usar do cadastro do carro)
    TIPO_TRAJETO_CHOICES = [
        ('CIDADE', 'Cidade (Urbano)'),
        ('ESTRADA', 'Estrada (Rodoviário)'),
        ('MISTO', 'Misto (Médio)'),
    ]
    tipo_trajeto = models.CharField(
        max_length=10,
        choices=TIPO_TRAJETO_CHOICES,
        default='CIDADE',
        verbose_name="Tipo de Trajeto"
    )

    valor_litro = models.DecimalField(
        max_digits=5, decimal_places=2, 
        default=0.00, 
        verbose_name="Preço do Litro (R$)"
    )

    # NOVO: Consumo Manual (Override)
    consumo_manual = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        verbose_name="Consumo Manual (Km/L)",
        help_text="Se preenchido, ignora o cadastro do veículo."
    )

    # --- TOTAIS ---
    km_total_apurado = DecimalField(max_digits=6, decimal_places=2, default=0.00, verbose_name="KM Total")
    tempo_total_min = models.IntegerField(default=0, verbose_name="Tempo Total (min)")
    custo_total_estimado = DecimalField(max_digits=6, decimal_places=2, default=0.00, verbose_name="Custo Total Estimado (R$)")
    
    observacoes = models.TextField(null=True, blank=True, verbose_name="Observações")

    # --- PROPRIEDADES AUXILIARES ---
    @property
    def origem_display(self):
        primeiro = self.percursos.order_by('sequencia').first()
        return primeiro.origem if primeiro else "N/A"

    @property
    def destino_display(self):
        ultimo = self.percursos.order_by('sequencia').last()
        return ultimo.destino if ultimo else "N/A"

    class Meta:
        verbose_name = "Dia de Deslocamento"
        verbose_name_plural = "Dias de Deslocamento"
        ordering = ['-data']

    def __str__(self):
        return f"Viagem de {self.data.strftime('%d/%m/%Y')} por {self.usuario.username}"


class Percurso(models.Model):
    """
    Representa um trecho entre dois pontos (perna) de uma viagem.
    """
    dia_de_deslocamento = models.ForeignKey(
        DiaDeDeslocamento, 
        on_delete=models.CASCADE,
        related_name="percursos"
    )
    sequencia = models.PositiveSmallIntegerField(verbose_name="Sequência")
    
    # Aumentado para 1000 conforme sua necessidade para endereços longos
    origem = models.CharField(max_length=1000, verbose_name="Origem")
    destino = models.CharField(max_length=1000, verbose_name="Destino")
    
    km_trecho = DecimalField(max_digits=6, decimal_places=2, verbose_name="KM Trecho")
    tempo_trecho_min = models.IntegerField(verbose_name="Tempo Trecho (min)")

    class Meta:
        verbose_name = "Percurso"
        verbose_name_plural = "Percursos"
        unique_together = ('dia_de_deslocamento', 'sequencia')
        ordering = ['sequencia']

    def __str__(self):
        return f"{self.sequencia}: {self.origem} -> {self.destino}"