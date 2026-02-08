from django.db import models
from django.conf import settings
from django.utils import timezone
import datetime

# Integração com Estoque
# Importamos ItemCasa para poder vincular o consumo específico (Geladeira/Armário)
from estoque.models import Estoque, ItemCasa

class Alimento(models.Model):
    """
    Representa os itens do seu MENU (Cardápio).
    Ex: 'Arroz Integral', 'Pizza', 'Whey Protein'.
    """
    CLASSIFICACAO_SAUDE = [
        ('SAUDAVEL', '✅ Saudável / Equilibrado'),
        ('MODERADO', '⚠️ Moderado'),
        ('LIXO', '❌ Lixo / Ultraprocessado'),
    ]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)
    classificacao = models.CharField(max_length=15, choices=CLASSIFICACAO_SAUDE, default='SAUDAVEL')
    
    # Calorias fica aqui para acesso rápido na listagem
    calorias = models.IntegerField(default=0, verbose_name="Kcal (aprox)")
    
    # Vinculo opcional com o Estoque (Genérico)
    item_estoque = models.ForeignKey(Estoque, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.nome

    @property
    def tem_tabela_nutricional(self):
        """Retorna True se houver dados nutricionais cadastrados."""
        return hasattr(self, 'nutricao')


class TabelaNutricional(models.Model):
    """
    Armazena os detalhes técnicos de nutrição.
    """
    # O related_name='nutricao' permite acessar assim: alimento.nutricao.proteinas
    alimento = models.OneToOneField(Alimento, on_delete=models.CASCADE, related_name='nutricao')
    
    # Macros Principais (Decimais para precisão, ex: 2.5g)
    proteinas = models.DecimalField("Proteínas (g)", max_digits=6, decimal_places=2, null=True, blank=True, default=0)
    carboidratos = models.DecimalField("Carboidratos (g)", max_digits=6, decimal_places=2, null=True, blank=True, default=0)
    gorduras_totais = models.DecimalField("Gorduras Totais (g)", max_digits=6, decimal_places=2, null=True, blank=True, default=0)
    
    # Detalhamento
    acucares = models.DecimalField("Açúcares (g)", max_digits=6, decimal_places=2, null=True, blank=True, default=0)
    sodio = models.DecimalField("Sódio (mg)", max_digits=8, decimal_places=2, null=True, blank=True, default=0)
    fibras = models.DecimalField("Fibras (g)", max_digits=6, decimal_places=2, null=True, blank=True, default=0)
    
    # Campo Flexível para Vitaminas, Minerais e %VD (Salva como JSON)
    outros_dados = models.JSONField("Outros / Vitaminas", default=dict, blank=True)

    def __str__(self):
        return f"Nutrição de {self.alimento.nome}"


class Refeicao(models.Model):
    """
    Representa o HISTÓRICO (O Diário Alimentar).
    Ex: 'No dia 12/12 comi Arroz Integral'.
    """
    TIPO_REFEICAO = [
        ('CAFE', '☕ Café da Manhã'),
        ('ALMOCO', '🍽️ Almoço'),
        ('LANCHE', '🍎 Lanche da Tarde'),
        ('JANTA', '🍲 Janta'),
        ('SOBREMESA', '🍰 Sobremesa'),
    ]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    data = models.DateField(default=datetime.date.today, verbose_name="Data")
    tipo = models.CharField(max_length=20, choices=TIPO_REFEICAO, default='ALMOCO')
    
    # Vinculamos aos alimentos cadastrados no menu (Manual)
    alimentos = models.ManyToManyField(Alimento, verbose_name="O que comeu?", blank=True)
    
    descricao_adicional = models.CharField(max_length=255, blank=True, null=True, verbose_name="Complemento", help_text="Ex: Com bastante salada")
    observacoes = models.TextField(blank=True, null=True, verbose_name="Obs / Sentimento")

    class Meta:
        verbose_name = "Refeição / Diário"
        verbose_name_plural = "Refeições"
        ordering = ['-data', '-id']

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.data}"
    
    @property
    def lista_alimentos(self):
        """Retorna string com nomes dos alimentos manuais"""
        return ", ".join([a.nome for a in self.alimentos.all()])
    
    @property
    def classificacao_geral(self):
        if self.alimentos.filter(classificacao='LIXO').exists():
            return 'LIXO'
        if self.alimentos.filter(classificacao='MODERADO').exists():
            return 'MODERADO'
        return 'SAUDAVEL'
    
    @property
    def total_calorias(self):
        return sum([a.calorias for a in self.alimentos.all()])
    
    @property
    def total_macros(self):
        macros = {'prot': 0, 'carb': 0, 'gord': 0}
        for item in self.alimentos.all():
            if hasattr(item, 'nutricao'):
                macros['prot'] += item.nutricao.proteinas or 0
                macros['carb'] += item.nutricao.carboidratos or 0
                macros['gord'] += item.nutricao.gorduras_totais or 0
        return macros


class ConsumoEstoque(models.Model):
    """
    [NOVO] Tabela intermediária para INTEGRAÇÃO COM ESTOQUE.
    Registra quais itens da Casa (ItemCasa) foram consumidos nesta refeição.
    Permite:
    1. Saber de onde saiu (ItemCasa -> Localização)
    2. Saber quanto saiu (quantidade)
    3. Devolver ao estoque se a refeição for excluída (Estorno)
    """
    refeicao = models.ForeignKey(Refeicao, on_delete=models.CASCADE, related_name='itens_estoque')
    
    # PROTECT: Impede deletar o item do estoque se houver histórico de consumo,
    # garantindo a integridade dos dados históricos.
    item_estoque = models.ForeignKey(ItemCasa, on_delete=models.PROTECT) 
    
    quantidade = models.DecimalField(max_digits=10, decimal_places=3)
    
    def __str__(self):
        return f"{self.item_estoque.nome} ({self.quantidade}) na Refeição {self.refeicao.id}"