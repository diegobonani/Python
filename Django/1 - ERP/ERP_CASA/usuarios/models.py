# usuarios/models.py

from django.db import models
from django.conf import settings # Para referenciar o User nativo

class Perfil(models.Model):
    # Tipos de Usuário
    TIPO_ADMINISTRADOR = 'Administrador'
    TIPO_USUARIO_COMUM = 'Usuário Comum'
    TIPOS_USUARIO_CHOICES = [
        (TIPO_ADMINISTRADOR, 'Administrador'),
        (TIPO_USUARIO_COMUM, 'Usuário Comum'),
    ]

    # Sexo
    SEXO_MASCULINO = 'M'
    SEXO_FEMININO = 'F'
    SEXO_CHOICES = [
        (SEXO_MASCULINO, 'Masculino'),
        (SEXO_FEMININO, 'Feminino'),
    ]

    # Relação um-para-um com o User nativo do Django
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    # Campo da sua tabela 'usuarios' original
    tipo = models.CharField(max_length=20, choices=TIPOS_USUARIO_CHOICES, default=TIPO_USUARIO_COMUM)

    # Campos da sua tabela 'usuarios_dados_pessoais'
    nome_completo = models.CharField(max_length=255)
    sexo = models.CharField(max_length=1, choices=SEXO_CHOICES, null=True, blank=True)
    data_nascimento = models.DateField(null=True, blank=True)
    rg = models.CharField(max_length=20, null=True, blank=True)
    cpf = models.CharField(max_length=20, null=True, blank=True)
    cnh = models.CharField(max_length=20, null=True, blank=True)
    altura = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    peso = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # ==========================================================
    # --- NOVOS CAMPOS (MÓDULO JORNADA) ---
    # ==========================================================

    # --- Os "Interruptores" Booleanos ---
    esta_trabalhando = models.BooleanField(
        default=False,
        verbose_name="Está trabalhando atualmente?"
    )
    esta_estudando = models.BooleanField(
        default=False,
        verbose_name="Está estudando atualmente?"
    )

    # --- Campos Auxiliares para "Modo Trabalho" ---
    # (Para o cálculo de salário que você pediu)
    valor_hora = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, 
        verbose_name="Valor da Hora (R$)",
        help_text="Preencha apenas se 'Está trabalhando' for verdadeiro."
    )

    salario_mensal_bruto = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, 
        verbose_name="Salário Mensal Bruto (R$)",
        help_text="Usado como referência. Os cálculos são feitos por hora."
    )
    
    percentual_hora_extra = models.DecimalField(
        max_digits=5, decimal_places=2, default=50.0, 
        verbose_name="Percentual da Hora Extra (%)",
        help_text="Ex: 50 para 50%, 100 para 100%."
    )
    
    # ==========================================================
    # --- FIM DA ADIÇÃO ---
    # ==========================================================


    def __str__(self):
        return self.usuario.username

# Adicione esta nova classe no final do arquivo
class UsuarioLegado(models.Model):
    # Mapeamento exato dos campos da sua tabela 'usuarios'
    id = models.IntegerField(primary_key=True)
    nome_usuario = models.CharField(max_length=100)
    senha = models.CharField(max_length=255)
    tipo = models.CharField(max_length=100) # Usaremos CharField para o ENUM
    user_permissao_total = models.IntegerField()

    class Meta:
        managed = False  # MUITO IMPORTANTE: Diz ao Django para não tocar nesta tabela
        db_table = 'usuarios'  # O nome exato da sua tabela no banco de dados