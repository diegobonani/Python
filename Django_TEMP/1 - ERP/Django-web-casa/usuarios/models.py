from django.db import models
from django.conf import settings 

class Perfil(models.Model):
    # ==========================================================
    # 1. CONFIGURAÇÕES BÁSICAS E RELACIONAMENTO
    # ==========================================================
    
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='perfil'
    )

    foto = models.ImageField(
        upload_to='perfil/', 
        null=True, blank=True, 
        verbose_name="Foto de Perfil"
    )

    # Tipos de Usuário
    TIPO_ADMINISTRADOR = 'Administrador'
    TIPO_USUARIO_COMUM = 'Usuário Comum'
    TIPO_FILHO = 'FILHO' 
    
    TIPOS_USUARIO_CHOICES = [
        (TIPO_ADMINISTRADOR, 'Administrador'),
        (TIPO_USUARIO_COMUM, 'Usuário Comum'),
        (TIPO_FILHO, 'Filho / Estudante'), 
    ]
    tipo = models.CharField(max_length=20, choices=TIPOS_USUARIO_CHOICES, default=TIPO_USUARIO_COMUM)

    # Vínculo Familiar
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='dependentes',
        verbose_name="Responsável (Pai/Mãe)"
    )

    # ==========================================================
    # 2. DADOS PESSOAIS
    # ==========================================================
    SEXO_MASCULINO = 'M'
    SEXO_FEMININO = 'F'
    SEXO_CHOICES = [
        (SEXO_MASCULINO, 'Masculino'),
        (SEXO_FEMININO, 'Feminino'),
    ]

    nome_completo = models.CharField(max_length=255)
    sexo = models.CharField(max_length=1, choices=SEXO_CHOICES, null=True, blank=True)
    data_nascimento = models.DateField(null=True, blank=True)
    rg = models.CharField(max_length=20, null=True, blank=True)
    cpf = models.CharField(max_length=20, null=True, blank=True)
    cnh = models.CharField(max_length=20, null=True, blank=True)
    altura = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    peso = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # ==========================================================
    # 3. GATILHOS DE MÓDULOS (PERMISSÕES VISUAIS)
    # ==========================================================
    esta_trabalhando = models.BooleanField(
        default=False,
        verbose_name="Módulo Jornada (Trabalho) Ativo?",
        help_text="Se marcado, exibe o menu 'Jornada' para este usuário."
    )
    
    # --- CONTROLE DE ESTUDOS ---
    esta_estudando = models.BooleanField(
        default=False,
        verbose_name="É Estudante Escolar? (Aba Escola)",
        help_text="Marque para quem frequenta escola regular (Leandro, Manu, etc)."
    )

    # NOVO CAMPO:
    esta_fazendo_curso = models.BooleanField(
        default=False,
        verbose_name="Faz Cursos Extras? (Aba Cursos)",
        help_text="Marque para quem faz cursos livres/Netflix (Diego, Jéssica, Crianças)."
    )

    # ==========================================================
    # 4. GAMIFICAÇÃO & FINANÇAS
    # ==========================================================
    saldo_pontos = models.IntegerField(
        default=0, 
        verbose_name="Saldo de Pontos (XP)",
        help_text="Pontos acumulados em estudos/tarefas. Pode ser convertido em saldo."
    )

    valor_hora = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, 
        verbose_name="Valor da Hora (R$)",
        help_text="Usado para calcular o pagamento no Ponto Eletrônico."
    )

    salario_mensal_bruto = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, 
        verbose_name="Salário Mensal Bruto (R$)",
        help_text="Apenas informativo."
    )
    
    percentual_hora_extra = models.DecimalField(
        max_digits=5, decimal_places=2, default=50.0, 
        verbose_name="Percentual Hora Extra (%)"
    )

    # ==========================================================
    # 5. DADOS ESCOLARES (Integração SED)
    # ==========================================================
    ra_numero = models.CharField(
        max_length=30, 
        blank=True, 
        null=True, 
        verbose_name="Número do RA",
        help_text="Apenas números (Ex: 123456789)"
    )
    ra_digito = models.CharField(
        max_length=5, 
        blank=True, 
        null=True, 
        verbose_name="Dígito RA",
        help_text="Ex: X, 1, 2"
    )
    ra_uf = models.CharField(
        max_length=2, 
        default='SP', 
        verbose_name="UF do RA",
        help_text="Estado (Ex: SP)"
    )
    senha_sed = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        verbose_name="Senha SED (Escola)",
        help_text="Senha para o robô acessar o boletim automaticamente"
    )

    def __str__(self):
        return f"Perfil: {self.nome_completo or self.usuario.username}"

    def pode_ganhar_pontos(self):
        if self.usuario.is_superuser or self.usuario.is_staff:
            return False
        if self.tipo == self.TIPO_ADMINISTRADOR:
            return False
        return True


# ==========================================================
# 6. HISTÓRICO DE RESET DE PONTOS
# ==========================================================
class HistoricoResetPontos(models.Model):
    data_reset = models.DateTimeField(auto_now_add=True, verbose_name="Data do Reset")
    
    realizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        verbose_name="Realizado por"
    )
    
    qtd_usuarios_afetados = models.IntegerField(verbose_name="Usuários Zerados")
    total_pontos_removidos = models.IntegerField(verbose_name="Total de Pontos Zerados")
    observacao = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-data_reset']
        verbose_name = "Histórico de Reset"
        verbose_name_plural = "Histórico de Resets"

    def __str__(self):
        autor = self.realizado_por.username if self.realizado_por else "SISTEMA AUTOMÁTICO"
        return f"{self.data_reset.strftime('%d/%m/%Y')} - {autor}"


# ==========================================================
# 7. CLASSE LEGADO
# ==========================================================
class UsuarioLegado(models.Model):
    id = models.IntegerField(primary_key=True)
    nome_usuario = models.CharField(max_length=100)
    senha = models.CharField(max_length=255)
    tipo = models.CharField(max_length=100)
    user_permissao_total = models.IntegerField()

    class Meta:
        managed = True
        db_table = 'usuarios'