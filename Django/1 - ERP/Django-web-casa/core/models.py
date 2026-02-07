from django.db import models

# ===================================================================
# 1. MODELOS AUXILIARES E DE ESTOQUE (MANTIDOS)
# ===================================================================

class Unidade(models.Model):
    sigla = models.CharField(max_length=10, unique=True, verbose_name="Sigla (Ex: UN, KG)")
    descricao = models.CharField(max_length=50, verbose_name="Descrição (Ex: Unidade, Quilograma)")
    permite_decimal = models.BooleanField(
        default=True, 
        verbose_name="Permite Decimal?",
        help_text="Desmarque se esta unidade só aceita números inteiros (Ex: Peça, Caixa)."
    )

    def __str__(self):
        return f"{self.sigla} - {self.descricao}"

class EstoqueSegmento(models.Model):
    nome_segmento = models.CharField(max_length=255, verbose_name="Nome do Segmento/Regra") 
    def __str__(self): return self.nome_segmento

class EstoqueCategoria(models.Model):
    nome_categoria = models.CharField(max_length=255, verbose_name="Nome da Categoria")
    segmentacao = models.ManyToManyField(
        EstoqueSegmento,
        blank=True, 
        help_text="Selecione as regras de visibilidade para esta categoria."
    )
    
    class Meta:
        verbose_name = "Categoria de Estoque"
        verbose_name_plural = "Categorias de Estoque"

    def __str__(self): return self.nome_categoria

class EquipamentoCategoria(models.Model):
    nome = models.CharField(max_length=100, unique=True, verbose_name="Nome da Categoria")
    class Meta:
        verbose_name = "Categoria de Equipamento"
        verbose_name_plural = "Categorias de Equipamentos"
    def __str__(self): return self.nome

class Equipamento(models.Model):
    nome = models.CharField(max_length=100, verbose_name="Nome do Equipamento (Ex: TV da Sala)")
    categoria = models.ForeignKey(EquipamentoCategoria, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Categoria")
    marca = models.CharField(max_length=100, blank=True, null=True)
    modelo = models.CharField(max_length=100, blank=True, null=True)
    localizacao = models.CharField(max_length=100, default="Casa")
    mac_address = models.CharField(
        max_length=17, blank=True, null=True, unique=True,
        verbose_name="Endereço MAC",
        help_text="Deixe em branco se não for um dispositivo de rede (ex: Fogão)."
    )
    capacidade_kg = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Apenas para Máquinas de Lavar: Capacidade máxima em KG"
    )

    def __str__(self): return self.nome

class Pet(models.Model):
    nome_pet = models.CharField(max_length=255, verbose_name="Nome do Animal")
    tipo_de_animal = models.CharField(max_length=255, verbose_name="Tipo de Animal")
    data_cadastro = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.nome_pet


# ===================================================================
# 2. NOVA HIERARQUIA FÍSICA (IMÓVEL DETALHADO -> CÔMODO -> LOCALIZAÇÃO)
# ===================================================================

class Setor(models.Model):
    """
    NÍVEL LÓGICO: Define o macro-grupo do sistema.
    Mantido para compatibilidade com o Estoque (CASA, PET, USUARIO).
    """
    nome = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nome

class Imovel(models.Model):
    """
    NÍVEL 1 FÍSICO: Cadastro detalhado da Propriedade.
    """
    # --- Identificação Principal ---
    nome = models.CharField(max_length=100, unique=True, verbose_name="Apelido do Imóvel", help_text="Ex: Casa Antiga, Apê Novo, Chácara")
    
    TIPO_CHOICES = [
        ('CASA', 'Casa Térrea/Sobrado'),
        ('APTO', 'Apartamento'),
        ('KITNET', 'Kitnet/Studio'),
        ('SITIO', 'Sítio/Chácara'),
        ('COMERCIAL', 'Sala Comercial'),
    ]
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='CASA', verbose_name="Tipo do Imóvel")

    FINALIDADE_CHOICES = [
        ('MORADIA', 'Minha Moradia Atual'),
        ('ALUGUEL', 'Imóvel de Aluguel/Renda'),
        ('VERANEIO', 'Casa de Praia/Campo'),
        ('VENDA', 'À Venda'),
        ('OUTRO', 'Outro'),
    ]
    finalidade = models.CharField(max_length=20, choices=FINALIDADE_CHOICES, default='MORADIA')

    # --- Endereço Completo ---
    cep = models.CharField(max_length=9, verbose_name="CEP", blank=True, null=True)
    logradouro = models.CharField(max_length=255, verbose_name="Logradouro", help_text="Rua, Avenida, Alameda...", blank=True, null=True)
    numero = models.CharField(max_length=20, verbose_name="Número", blank=True, null=True)
    complemento = models.CharField(max_length=100, blank=True, null=True, help_text="Ex: Casa 2, Fundos")
    bairro = models.CharField(max_length=100, blank=True, null=True)
    cidade = models.CharField(max_length=100, blank=True, null=True)
    uf = models.CharField(max_length=2, verbose_name="UF", blank=True, null=True)

    # --- Detalhes de Condomínio / Vertical ---
    eh_condominio = models.BooleanField(default=False, verbose_name="É Condomínio?")
    nome_condominio = models.CharField(max_length=150, blank=True, null=True, verbose_name="Nome do Condomínio")
    bloco_torre = models.CharField(max_length=50, blank=True, null=True, verbose_name="Bloco/Torre")
    quadra = models.CharField(max_length=50, blank=True, null=True, verbose_name="Quadra/Praça")
    andar = models.CharField(max_length=10, blank=True, null=True, verbose_name="Andar")
    unidade_apto = models.CharField(max_length=20, blank=True, null=True, verbose_name="Nº Apto/Unidade")

    # --- Características Técnicas (Opcionais) ---
    metragem = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Área Total (m²)")
    qtd_comodos_estimada = models.IntegerField(blank=True, null=True, verbose_name="Qtd. Cômodos", help_text="Apenas para referência")
    
    observacoes = models.TextField(blank=True, null=True, verbose_name="Notas Gerais")

    class Meta:
        verbose_name = "Imóvel Detalhado"
        verbose_name_plural = "Imóveis"

    def __str__(self):
        local = f" - {self.cidade}" if self.cidade else ""
        return f"{self.nome} ({self.get_tipo_display()}){local}"

class Comodo(models.Model):
    """
    NÍVEL 2 FÍSICO: Os ambientes dentro de UM Imóvel específico.
    Ex: 'Cozinha' (da Casa Antiga) vs 'Cozinha' (do Novo Apê).
    """
    # Vínculo com o Imóvel Detalhado
    imovel = models.ForeignKey(
        Imovel, 
        on_delete=models.CASCADE, 
        related_name='comodos', 
        null=True, # Importante para a migração inicial
        blank=True, 
        verbose_name="Pertence ao Imóvel"
    )
    
    nome = models.CharField(max_length=50, verbose_name="Nome do Cômodo")

    class Meta:
        verbose_name = "Cômodo"
        verbose_name_plural = "Cômodos"
        unique_together = ('imovel', 'nome') # Evita nomes repetidos no MESMO imóvel

    def __str__(self):
        origem = self.imovel.nome if self.imovel else "Sem Imóvel Definido"
        return f"{self.nome} ({origem})"

class Localizacao(models.Model):
    """
    NÍVEL 3 FÍSICO: O local exato dentro do Cômodo.
    Ex: 'Armário Aéreo', 'Gaveta 1'.
    """
    comodo = models.ForeignKey(
        Comodo, 
        on_delete=models.CASCADE, 
        related_name='localizacoes', 
        verbose_name="Pertence ao Cômodo"
    )
    nome = models.CharField(max_length=100, verbose_name="Nome da Localização/Móvel")

    class Meta:
        verbose_name = "Localização Específica"
        verbose_name_plural = "Localizações Específicas"
        unique_together = ('comodo', 'nome')

    def __str__(self):
        return f"{self.nome} - {self.comodo.nome}"