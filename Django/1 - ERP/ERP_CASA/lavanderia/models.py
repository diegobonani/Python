from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from django.db.models import Sum

# Importa os modelos dos apps 'core' e 'estoque'
from core.models import Equipamento
# Importamos ItemCasa, pois é lá que estão Sabão, Amaciante, etc.
from estoque.models import ItemCasa 

class CestoDeRoupas(models.Model):
    """
    Representa um cesto de roupas sujas aguardando lavagem.
    """
    TIPO_ROUPA_CHOICES = [
        ('ESCURAS', 'Roupas Escuras'), 
        ('BRANCAS', 'Roupas Brancas'), 
        ('CAMA_BANHO', 'Roupas de Cama e Banho'), 
        ('DELICADAS', 'Roupas Delicadas'), 
        ('PET', 'Roupas do Pet')
    ]
    STATUS_CHOICES = [
        ('AGUARDANDO', 'Aguardando Lavagem'), 
        ('EM_LAVAGEM', 'Em Lavagem'), 
        ('CONCLUIDO', 'Concluído'), # Significa que já foi lavado e guardado
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, help_text="Dono das roupas (deixe em branco se for da casa)")
    tipo_roupa = models.CharField(max_length=20, choices=TIPO_ROUPA_CHOICES, verbose_name="Tipo de Roupa")
    
    # Campo de entrada do usuário
    quantidade_cestos = models.DecimalField(
        max_digits=4, 
        decimal_places=2, 
        default=1.0, 
        verbose_name="Quantidade de Cestos (1 cesto = 40L)"
    )
    # Campo calculado
    peso_kg = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        verbose_name="Peso Estimado (kg)", 
        default=0.0, 
        editable=False # O usuário não pode editar isso
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='AGUARDANDO')
    prioridade = models.BooleanField(default=False, verbose_name="É urgente?")
    data_adicionado = models.DateTimeField(default=timezone.now)
    
    # O "link" que move o cesto da fila para um ciclo ativo
    ciclo_associado = models.ForeignKey(
        'CicloLavagem', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="cestos"
    )

    # A "Heurística" de Conversão (1 Cesto 40L -> KG)
    TAXAS_DE_CONVERSAO_KG = {
        'ESCURAS': Decimal('4.5'), 
        'BRANCAS': Decimal('4.5'),
        'CAMA_BANHO': Decimal('6.0'), # Mais pesado
        'DELICADAS': Decimal('3.0'), # Mais leve
        'PET': Decimal('4.0'),
    }

    def save(self, *args, **kwargs):
        # ANTES DE SALVAR, CALCULA O PESO
        taxa = self.TAXAS_DE_CONVERSAO_KG.get(self.tipo_roupa, Decimal('4.0'))
        self.peso_kg = self.quantidade_cestos * taxa
        super().save(*args, **kwargs)

    @property
    def dias_aguardando(self):
        if self.status == 'AGUARDANDO':
            return (timezone.now() - self.data_adicionado).days
        return 0

    def __str__(self):
        dono = "Casa"
        if self.tipo_roupa == 'PET': dono = "Pet"
        elif self.usuario: dono = self.usuario.username.capitalize()
        return f"Cesto de {self.get_tipo_roupa_display()} ({dono})"

class CicloLavagem(models.Model):
    """
    Representa um ciclo de lavagem real (o "Gêmeo Digital").
    """
    STATUS_PROCESSO_CHOICES = [
        ('LAVANDO', 'Lavando'),
        ('ENXAGUANDO', 'Enxaguando'),
        ('CENTRIFUGANDO', 'Centrifugando'),
        ('SECANDO_VARAL', 'Secando (Varal)'),
        ('CONCLUIDO', 'Concluído (Guardado)'),
    ]

    equipamento = models.ForeignKey(Equipamento, on_delete=models.PROTECT, related_name="ciclos")
    usuario_responsavel = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    data_hora_inicio = models.DateTimeField(default=timezone.now)
    data_hora_fim = models.DateTimeField(null=True, blank=True)
    
    # Campos do Gêmeo Digital
    status_processo = models.CharField(max_length=20, choices=STATUS_PROCESSO_CHOICES, default='LAVANDO')
    data_hora_inicio_etapa = models.DateTimeField(default=timezone.now)
    
    # Link direto com os itens consumidos (agora apontando para ItemCasa)
    produtos_consumidos = models.ManyToManyField(ItemCasa, through='ProdutoConsumidoLavagem', blank=True)
    
    @property
    def peso_total_lavado(self):
        # Soma o peso de todos os cestos associados a este ciclo
        total = self.cestos.aggregate(total=Sum('peso_kg'))['total']
        return total or 0
    
    @property
    def tempo_na_etapa_atual(self):
        # Calcula há quanto tempo está na etapa atual
        return timezone.now() - self.data_hora_inicio_etapa

    def __str__(self):
        return f"Ciclo #{self.id} ({self.get_status_processo_display()})"

class ProdutoConsumidoLavagem(models.Model):
    """ Tabela de ligação entre CicloLavagem e ItemCasa (Estoque de Insumos). """
    ciclo = models.ForeignKey(CicloLavagem, on_delete=models.CASCADE)
    
    # MUDANÇA CRUCIAL: Aponta para ItemCasa, não Estoque Genérico
    produto_estoque = models.ForeignKey(ItemCasa, on_delete=models.PROTECT, verbose_name="Insumo (Sabão/Amaciante)")
    
    quantidade_consumida = models.DecimalField(max_digits=10, decimal_places=3)

    class Meta:
        unique_together = ('ciclo', 'produto_estoque')
        verbose_name = "Produto Consumido"
        verbose_name_plural = "Produtos Consumidos"