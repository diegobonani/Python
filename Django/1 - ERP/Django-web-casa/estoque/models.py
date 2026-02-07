from django.db import models
from django.conf import settings
from django.db.models import Sum, F, Value, DecimalField
from django.db.models.functions import Coalesce
from decimal import Decimal

# Imports de outros apps (Garante integridade das Foreign Keys)
from core.models import Unidade, EstoqueCategoria, Pet, Imovel, Comodo, Localizacao

# ===================================================================
# 1. TABELAS DETALHADAS (ITENS REAIS)
# ===================================================================

class ItemCasa(models.Model):
    # Relacionamentos de Localização (Opcionais para evitar travamento)
    comodo = models.ForeignKey(Comodo, on_delete=models.SET_NULL, null=True, blank=True)
    localizacao = models.ForeignKey(Localizacao, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Dados Básicos
    nome = models.CharField(max_length=255)
    categoria = models.ForeignKey(EstoqueCategoria, on_delete=models.SET_NULL, null=True, blank=True)
    unidade = models.ForeignKey(Unidade, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Valores Numéricos (Decimal para precisão financeira/estoque)
    quantidade = models.DecimalField(max_digits=10, decimal_places=3, default=1.000)
    preco = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Controle de Estoque
    estoque_minimo = models.DecimalField(max_digits=10, decimal_places=3, default=1.000)
    estoque_ideal = models.DecimalField(max_digits=10, decimal_places=3, default=2.000)
    
    # Metadados
    validade = models.DateField(null=True, blank=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)

    @property
    def preco_total(self):
        return self.quantidade * self.preco

    def __str__(self):
        return self.nome

class ItemPet(models.Model):
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='itens')
    nome = models.CharField(max_length=255)
    categoria = models.ForeignKey(EstoqueCategoria, on_delete=models.SET_NULL, null=True, blank=True)
    unidade = models.ForeignKey(Unidade, on_delete=models.SET_NULL, null=True, blank=True)
    quantidade = models.DecimalField(max_digits=10, decimal_places=3, default=1.000)
    preco = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    estoque_minimo = models.DecimalField(max_digits=10, decimal_places=3, default=1.000)
    estoque_ideal = models.DecimalField(max_digits=10, decimal_places=3, default=2.000)
    validade = models.DateField(null=True, blank=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)

    @property
    def preco_total(self):
        return self.quantidade * self.preco

    def __str__(self):
        return f"{self.nome} ({self.pet.nome_pet})"

class ItemUsuario(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='itens_estoque')
    nome = models.CharField(max_length=255)
    categoria = models.ForeignKey(EstoqueCategoria, on_delete=models.SET_NULL, null=True, blank=True)
    quantidade = models.DecimalField(max_digits=10, decimal_places=3, default=1.000)
    estoque_minimo = models.DecimalField(max_digits=10, decimal_places=3, default=1.000)
    estoque_ideal = models.DecimalField(max_digits=10, decimal_places=3, default=2.000)
    data_cadastro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nome} ({self.usuario.username})"

# ===================================================================
# 2. HUB CENTRAL (CONSOLIDADOR)
# ===================================================================

class Estoque(models.Model):
    SETOR_CHOICES = [('USUARIO', 'Usuário'), ('PET', 'Pet'), ('CASA', 'Casa')]
    setor = models.CharField(max_length=10, choices=SETOR_CHOICES)
    
    # Relacionamentos Um-para-Um (Cada linha do HUB aponta para UM item detalhado)
    item_casa = models.OneToOneField(ItemCasa, on_delete=models.CASCADE, null=True, blank=True)
    item_pet = models.OneToOneField(ItemPet, on_delete=models.CASCADE, null=True, blank=True)
    item_usuario = models.OneToOneField(ItemUsuario, on_delete=models.CASCADE, null=True, blank=True)
    
    data_cadastro = models.DateTimeField(auto_now_add=True)

    @property
    def get_detalhe(self):
        """ Retorna o objeto filho real baseado no setor """
        if self.setor == 'CASA': return self.item_casa
        if self.setor == 'PET': return self.item_pet
        if self.setor == 'USUARIO': return self.item_usuario
        return None
    
    @property
    def valor_total_estoque(self):
        """ Calcula valor total monetário do item """
        detalhe = self.get_detalhe
        if detalhe and hasattr(detalhe, 'preco') and hasattr(detalhe, 'quantidade'):
            return detalhe.quantidade * detalhe.preco
        return Decimal('0.00')

    def __str__(self):
        return f"HUB #{self.pk} [{self.setor}]"

# ===================================================================
# 3. HISTÓRICO E LOGS
# ===================================================================

class EstoqueLog(models.Model):
    """ Log legado (Texto) - Mantido para segurança de auditoria """
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    acao = models.CharField(max_length=10)
    data_hora = models.DateTimeField(auto_now_add=True)
    item_nome = models.CharField(max_length=255)
    item_setor = models.CharField(max_length=50)
    item_dono = models.CharField(max_length=100, blank=True)
    item_categoria = models.CharField(max_length=100, blank=True, null=True)
    quantidade_antiga = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    quantidade_nova = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    
    class Meta:
        ordering = ['-data_hora']

class HistoricoEstoque(models.Model):
    """ 
    [ATUALIZADO] Histórico com proteção contra exclusão (Snapshot).
    Usa SET_NULL para manter o log mesmo se o item original for deletado.
    """
    # MUDANÇA 1: on_delete=SET_NULL permite que o histórico sobreviva à exclusão do item
    estoque = models.ForeignKey(
        'Estoque', # Usa string para evitar erro de importação circular se houver
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='historico_relacional'
    )
    
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    data_movimento = models.DateTimeField(auto_now_add=True)
    
    TIPO_MOVIMENTO_CHOICES = [
        ('CRIACAO', 'Criação'),
        ('BAIXA', 'Baixa'),
        ('EDICAO', 'Edição'),
        ('EXCLUSAO', 'Exclusão'),
        ('COMPRA', 'Compra')
    ]
    tipo_movimento = models.CharField(max_length=20, choices=TIPO_MOVIMENTO_CHOICES)
    
    # Snapshot dos valores (Qtd e Saldos)
    quantidade_movimentada = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    saldo_anterior = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    saldo_atual = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    
    # MUDANÇA 2: Novos campos para guardar o "Nome" e "Local" eternamente (Texto)
    item_nome_snapshot = models.CharField(max_length=255, blank=True, null=True)
    item_local_snapshot = models.CharField(max_length=255, blank=True, null=True)

    # Mudei para TextField para caber observações longas de sistema
    observacao = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-data_movimento']

    def __str__(self):
        return f"{self.tipo_movimento} - {self.data_movimento}"

# ===================================================================
# 4. COMPRAS E SIMULAÇÃO
# ===================================================================

class ListaCompra(models.Model):
    supermercado = models.CharField(max_length=255)
    cidade = models.CharField(max_length=100)
    data_compra = models.DateField()
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    url_nota = models.CharField(max_length=500,blank=True,null=True,unique=True,verbose_name="URL / Link da Nota")
    chave_acesso = models.CharField(max_length=44, blank=True, null=True, verbose_name="Chave de Acesso")
    detalhada = models.BooleanField(default=True)
    lancamento_financeiro_criado = models.BooleanField(default=False)
    
    @property
    def item_count(self):
        return self.produtos.count()
    
    @property
    def tipo_compra(self):
        return 'IMPORTADA' if self.url_nota else 'MANUAL'
    
    def save(self, *args, **kwargs):
        if self.detalhada and self.pk:
            total = self.produtos.aggregate(
                t=Coalesce(Sum(F('quantidade') * F('valor_unit')), Value(0, output_field=DecimalField()))
            )['t']
            self.valor_total = total
        super().save(*args, **kwargs)

class ListaCompraProduto(models.Model):
    compra = models.ForeignKey(ListaCompra, on_delete=models.CASCADE, related_name='produtos')
    nome = models.CharField(max_length=255)
    marca = models.CharField(max_length=100, null=True, blank=True)
    quantidade = models.DecimalField(max_digits=10, decimal_places=3, default=1.000)
    unidade = models.ForeignKey(Unidade, on_delete=models.SET_NULL, null=True, blank=True)
    valor_unit = models.DecimalField(max_digits=10, decimal_places=2)
    adicionado_ao_estoque = models.BooleanField(default=False)
    comodo_destino = models.ForeignKey(Comodo, on_delete=models.SET_NULL, null=True, blank=True)
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.compra.save()

class SimulacaoCenario(models.Model):
    nome = models.CharField(max_length=200)
    usuario_criador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    data_criacao = models.DateTimeField(auto_now_add=True)

class SimulacaoItem(models.Model):
    cenario = models.ForeignKey(SimulacaoCenario, on_delete=models.CASCADE, related_name='itens')
    nome_item = models.CharField(max_length=200)
    preco_estimado = models.DecimalField(max_digits=10, decimal_places=2)
    quantidade = models.DecimalField(max_digits=10, decimal_places=3, default=1.0)
    observacoes = models.TextField(blank=True, null=True)

# ==============================================================================
# 5. ASSISTENTE DE REPOSIÇÃO
# ==============================================================================

class CatalogoPessoal(models.Model):
    SETOR_CHOICES = [('CASA', 'Casa'), ('PET', 'Pets'), ('USUARIO', 'Usuários')]
    nome = models.CharField(max_length=100)
    categoria = models.ForeignKey(EstoqueCategoria, on_delete=models.SET_NULL, null=True, blank=True)
    setor = models.CharField(max_length=20, choices=SETOR_CHOICES, default='USUARIO') 
    
    def __str__(self):
        return f"{self.nome} ({self.get_setor_display()})"
    
    class Meta:
        unique_together = ('nome', 'setor') 

class ItemFaltante(models.Model):
    PRIORIDADE_CHOICES = [(1, 'Baixa'), (2, 'Média'), (3, 'Alta')]
    item_catalogo = models.ForeignKey(CatalogoPessoal, on_delete=models.CASCADE)
    
    # Destinos possíveis
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, null=True, blank=True)
    comodo = models.ForeignKey(Comodo, on_delete=models.CASCADE, null=True, blank=True)
    localizacao = models.ForeignKey(Localizacao, on_delete=models.CASCADE, null=True, blank=True)
    
    # Dados de compra
    quantidade = models.DecimalField(max_digits=10, decimal_places=3, default=1.000)
    unidade = models.ForeignKey(Unidade, on_delete=models.SET_NULL, null=True, blank=True)
    prioridade = models.IntegerField(choices=PRIORIDADE_CHOICES, default=2)
    observacao = models.CharField(max_length=200, blank=True, null=True)
    data_adicionado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.item_catalogo.nome} ({self.quantidade})"

    @property
    def destinatario_nome(self):
        if self.usuario: return self.usuario.username
        if self.pet: return self.pet.nome_pet
        if self.localizacao: return f"{self.comodo.nome} > {self.localizacao.nome}"
        if self.comodo: return self.comodo.nome
        return "Geral"
    
    @property
    def setor_origem(self):
        if self.usuario: return 'USUARIO'
        if self.pet: return 'PET'
        if self.comodo: return 'CASA'
        return 'OUTRO'