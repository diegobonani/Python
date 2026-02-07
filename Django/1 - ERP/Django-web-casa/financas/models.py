from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Sum, Value, DecimalField
from django.db.models.functions import Coalesce
from estoque.models import ListaCompra
from datetime import date

# ===================================================================
# MODELOS AUXILIARES
# ===================================================================

class FinancaCategoria(models.Model):
    """
    Ex: Moradia, Transporte, Alimentação, Lazer.
    """
    TIPO_CUSTO_CHOICES = [('Fixas', 'Fixas'), ('Variadas', 'Variadas')]
    nome = models.CharField(max_length=100)
    tipo_custo = models.CharField(max_length=10, choices=TIPO_CUSTO_CHOICES)

    class Meta:
        verbose_name = "Categoria de Finança"
        verbose_name_plural = "Categorias de Finanças"

    def __str__(self):
        return self.nome

class ContaFinanceira(models.Model):
    """
    Ex: Carteira, Nubank, Itaú.
    Contas virtuais dos usuários (ex: Arthur) também entram aqui.
    """
    nome = models.CharField(max_length=100)
    saldo_inicial = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    is_shared = models.BooleanField(default=False, verbose_name="Conta da Casa")
    nao_permite_negativo = models.BooleanField(default=False)
    
    @property
    def saldo_atual(self):
        receitas = self.lancamentos.filter(tipo='Receitas').aggregate(
            total=Coalesce(Sum('valor'), Value(0.0, output_field=DecimalField()))
        )['total']
        despesas = self.lancamentos.filter(tipo='Despesas').aggregate(
            total=Coalesce(Sum('valor'), Value(0.0, output_field=DecimalField()))
        )['total']
        return self.saldo_inicial + receitas - despesas
        
    def __str__(self):
        dono = "Casa" if self.is_shared else (self.usuario.username if self.usuario else "Desconhecido")
        return f"{self.nome} ({dono})"

class FormaPagamento(models.Model):
    nome = models.CharField(max_length=50)
    def __str__(self): return self.nome

# ===================================================================
# NÚCLEO FINANCEIRO
# ===================================================================

class Financa(models.Model):
    """
    O Lançamento Financeiro Genérico (Header).
    Tudo converge para cá: Compras, Abastecimentos, Mesadas.
    """
    TIPO_CHOICES = [('Receitas', 'Receitas'), ('Despesas', 'Despesas')]
    CONTA_TIPO_CHOICES = [('Fixas', 'Fixas'), ('Variadas', 'Variadas')]
    
    # Campo novo para rastrear se veio do sistema de Rotinas
    ORIGEM_CHOICES = [
        ('MANUAL', 'Manual'),
        ('ROTINA', 'Rotina/Mesada'),
        ('IMPORT', 'Importação'),
    ]

    conta = models.ForeignKey(ContaFinanceira, on_delete=models.PROTECT, verbose_name="Conta", related_name='lancamentos')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100, verbose_name="Descrição")
    descricao = models.CharField(max_length=255, null=True, blank=True)
    
    categoria = models.ForeignKey(FinancaCategoria, on_delete=models.SET_NULL, null=True, blank=True)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    conta_tipo = models.CharField(max_length=10, choices=CONTA_TIPO_CHOICES, null=True, blank=True)
    origem = models.CharField(max_length=10, choices=ORIGEM_CHOICES, default='MANUAL') 
    
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    # Forma de pagamento aqui é a "principal". Se for parcelado, usa-se o model Pagamento abaixo.
    forma_pagamento = models.ForeignKey(FormaPagamento, on_delete=models.SET_NULL, null=True, blank=True)
    data_registro = models.DateField()

    # Vínculos Opcionais (Integrações)
    compra_associada = models.OneToOneField(ListaCompra, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-data_registro']

    def __str__(self):
        return f"{self.nome} - R$ {self.valor}"

    def save(self, *args, **kwargs):
        if self.categoria:
            self.conta_tipo = self.categoria.tipo_custo
        super().save(*args, **kwargs)

# ===================================================================
# DETALHAMENTO DE PAGAMENTOS E PARCELAS (NOVOS)
# ===================================================================
# 

class Pagamento(models.Model):
    """
    Detalhes da transação. Ex: Uma 'Financa' de R$ 1000,00 pode ter sido
    paga em 2 cartões diferentes ou parcelada.
    """
    STATUS_CHOICES = [('Pendente', 'Pendente'), ('Pago', 'Pago'), ('Atrasado', 'Atrasado')]

    financa = models.ForeignKey(Financa, on_delete=models.CASCADE, related_name='detalhes_pagamento')
    forma_pagamento = models.ForeignKey(FormaPagamento, on_delete=models.SET_NULL, null=True)
    parcelas = models.IntegerField(default=1)
    valor_pago = models.DecimalField(max_digits=10, decimal_places=2)
    data_pagamento = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Pendente')

    # Como renomeamos no SQL para 'financas_pagamento', o Django acha sozinho,
    # mas se quiser forçar para garantir:
    class Meta:
        db_table = 'financas_pagamento'

class Parcela(models.Model):
    """
    Controle individual de cada parcela.
    """
    STATUS_CHOICES = [('Pendente', 'Pendente'), ('Pago', 'Pago'), ('Atrasado', 'Atrasado')]

    financa = models.ForeignKey(Financa, on_delete=models.CASCADE, related_name='lista_parcelas')
    pagamento = models.ForeignKey(Pagamento, on_delete=models.CASCADE, related_name='parcelas_vinculadas', null=True, blank=True)
    
    numero_parcela = models.IntegerField(default=1) # Ex: 1 de 12
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_vencimento = models.DateField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Pendente')

    class Meta:
        db_table = 'financas_parcela'

# ===================================================================
# COMPROVANTES E SONHOS
# ===================================================================

class FinancaComprovante(models.Model):
    financa = models.ForeignKey(Financa, on_delete=models.CASCADE, related_name='comprovantes')
    arquivo = models.FileField(upload_to='comprovantes/%Y/%m/')
    descricao = models.TextField(null=True, blank=True)
    data_envio = models.DateTimeField(auto_now_add=True)

class CenarioFinanceiro(models.Model):
    TIPO_CHOICES = [
        ('imovel', 'Imóvel / Reforma'),
        ('veiculo', 'Veículo'),
        ('viagem', 'Viagem'),
        ('reserva', 'Reserva de Emergência'),
        ('outro', 'Outro'),
    ]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    titulo = models.CharField(max_length=100, verbose_name="Nome do Sonho")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    
    valor_total = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Valor Total (R$)")
    valor_entrada = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Entrada Disponível (R$)")
    poupanca_mensal_planejada = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Quanto guardar por mês?")
    
    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titulo