# Em: jornada/models.py

from django.db import models
from django.conf import settings 
from decimal import Decimal
import datetime

# --- Constantes para os Tipos de Dia (JORNADA NORMAL) ---
class TipoDiaJornada:
    NORMAL = 'NORMAL'
    SABADO = 'SABADO'
    FERIADO = 'FERIADO'
    PLANTAO = 'PLANTAO'
    FOLGA = 'FOLGA'
    ATESTADO = 'ATESTADO'
    
    CHOICES = [
        (NORMAL, 'Dia Normal (Semana)'),
        (SABADO, 'Sábado (Jornada Padrão)'),
        (FERIADO, 'Feriado (100%)'),
        (PLANTAO, 'Plantão (100%)'),
        (FOLGA, 'Folga (Descanso)'),
        (ATESTADO, 'Atestado Médico'),
    ]

# ===================================================================
# === 1. MODELO PARA A ABA "JORNADA" ===
# ===================================================================
class RegistroPonto(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name="registros_ponto"
    )
    data = models.DateField()
    
    tipo_dia = models.CharField(
        max_length=20,
        choices=TipoDiaJornada.CHOICES,
        default=TipoDiaJornada.NORMAL,
        verbose_name="Tipo de Dia"
    )
    
    entrada = models.TimeField(null=True, blank=True, verbose_name="Entrada")
    saida_almoco = models.TimeField(null=True, blank=True, verbose_name="Saída Almoço")
    retorno_almoco = models.TimeField(null=True, blank=True, verbose_name="Retorno Almoço")
    saida = models.TimeField(null=True, blank=True, verbose_name="Saída")
    
    atestado_cid = models.CharField(max_length=20, null=True, blank=True, verbose_name="CID")
    atestado_crm = models.CharField(max_length=20, null=True, blank=True, verbose_name="CRM Médico")
    atestado_obs = models.TextField(null=True, blank=True, verbose_name="Observação/Motivo")

    class Meta:
        unique_together = ('usuario', 'data', 'tipo_dia') 
        ordering = ['-data', 'entrada']
        verbose_name = "Registro de Ponto"
        verbose_name_plural = "Registros de Ponto"

    def __str__(self):
        return f"{self.usuario.username} - {self.data.strftime('%d/%m/%Y')} ({self.get_tipo_dia_display()})"

    # --- Funções de Cálculo (Propriedades) ATUALIZADAS ---
    
    @property
    def horas_almoco(self) -> Decimal:
        if self.tipo_dia != TipoDiaJornada.NORMAL:
            return Decimal('0.0')
        
        if self.saida_almoco and self.retorno_almoco:
            try:
                data_base = self.data
                dt_saida = datetime.datetime.combine(data_base, self.saida_almoco)
                dt_retorno = datetime.datetime.combine(data_base, self.retorno_almoco)
                segundos = (dt_retorno - dt_saida).total_seconds()
                return Decimal(segundos / 3600)
            except Exception:
                pass
        return Decimal('0.0')

    @property
    def horas_trabalhadas(self) -> Decimal:
        """ Calcula o total de horas (ignora se for folga) """
        
        # --- CORREÇÃO AQUI ---
        # Atestado DEVE calcular as horas (para pagar), Folga não.
        if self.tipo_dia == TipoDiaJornada.FOLGA:
            return Decimal('0.0')
        
        total_segundos = 0
        
        # Lógica para Dias Normais ou Atestado (com almoço)
        if self.tipo_dia == TipoDiaJornada.NORMAL or self.tipo_dia == TipoDiaJornada.ATESTADO:
            # (Se for Atestado, o forms.py já preencheu as horas de compensação)
            if self.entrada and self.saida_almoco:
                dt_e = datetime.datetime.combine(self.data, self.entrada)
                dt_sa = datetime.datetime.combine(self.data, self.saida_almoco)
                total_segundos += (dt_sa - dt_e).total_seconds()
            if self.retorno_almoco and self.saida:
                dt_ra = datetime.datetime.combine(self.data, self.retorno_almoco)
                dt_s = datetime.datetime.combine(self.data, self.saida)
                total_segundos += (dt_s - dt_ra).total_seconds()
            
            # Caso especial: Atestado de Sábado/Domingo (sem almoço)
            if self.tipo_dia == TipoDiaJornada.ATESTADO and not self.saida_almoco:
                 if self.entrada and self.saida:
                    dt_e = datetime.datetime.combine(self.data, self.entrada)
                    dt_s = datetime.datetime.combine(self.data, self.saida)
                    total_segundos = (dt_s - dt_e).total_seconds()

        else: # Sábado, Feriado, Plantão
            if self.entrada and self.saida:
                dt_e = datetime.datetime.combine(self.data, self.entrada)
                dt_s = datetime.datetime.combine(self.data, self.saida)
                total_segundos = (dt_s - dt_e).total_seconds()

        return Decimal(total_segundos / 3600)

    @property
    def horas_extras(self) -> Decimal:
        """ Calcula horas extras (ignora atestado ou folga) """
        
        # --- CORREÇÃO AQUI ---
        if self.tipo_dia in [TipoDiaJornada.ATESTADO, TipoDiaJornada.FOLGA]:
            return Decimal('0.0')
        
        horas = self.horas_trabalhadas
        
        if self.tipo_dia in [TipoDiaJornada.FERIADO, TipoDiaJornada.PLANTAO]:
            return horas 
            
        if self.tipo_dia == TipoDiaJornada.SABADO:
            jornada_padrao_sabado = Decimal('4.0')
            return max(Decimal('0.0'), horas - jornada_padrao_sabado)
            
        jornada_padrao_normal = Decimal('8.0')
        return max(Decimal('0.0'), horas - jornada_padrao_normal)

    @property
    def valor_receber(self) -> Decimal:
        """ Calcula o pagamento com base nas suas regras de negócio. """
        
        if self.tipo_dia == TipoDiaJornada.FOLGA:
            return Decimal('0.0')
            
        perfil = getattr(self.usuario, 'perfil', None)
        if not perfil or not perfil.valor_hora:
            return Decimal('0.0')

        valor_hora = perfil.valor_hora
        horas_trabalhadas = self.horas_trabalhadas
        
        if self.tipo_dia == TipoDiaJornada.ATESTADO:
            # Paga as horas compensadas (8h, 4h ou 5.5h) pelo valor normal
            return horas_trabalhadas * valor_hora
        
        if self.tipo_dia in [TipoDiaJornada.FERIADO, TipoDiaJornada.PLANTAO]:
            valor_hora_do_dia = valor_hora * 2
            return horas_trabalhadas * valor_hora_do_dia
            
        percentual_extra = perfil.percentual_hora_extra / Decimal('100.0')
        valor_hora_extra = valor_hora * (1 + percentual_extra)

        if self.tipo_dia == TipoDiaJornada.SABADO:
            jornada_padrao_horas = Decimal('4.0')
        else: # Dia Normal
            jornada_padrao_horas = Decimal('8.0')

        horas_normais = min(horas_trabalhadas, jornada_padrao_horas)
        horas_extras = max(Decimal('0.0'), horas_trabalhadas - jornada_padrao_horas)

        pagamento_normal = horas_normais * valor_hora
        pagamento_extra = horas_extras * valor_hora_extra
        
        return pagamento_normal + pagamento_extra

# ===================================================================
# === 2. MODELO PARA A ABA "BALANÇO" (NOVO) ===
# ===================================================================

def balanco_upload_path(instance, filename):
    return f'balancos/usuario_{instance.usuario.id}/{instance.data.year}/{instance.data.month}/{filename}'

class RegistroBalanço(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="balancos"
    )
    data = models.DateField(verbose_name="Data do Balanço")
    loja = models.CharField(max_length=100, verbose_name="Loja")
    entrada = models.TimeField(null=True, blank=True, verbose_name="Entrada")
    saida = models.TimeField(null=True, blank=True, verbose_name="Saída")
    
    anexo = models.FileField(
        upload_to=balanco_upload_path, 
        null=True, blank=True, 
        verbose_name="Anexo (Foto/Vídeo)"
    )

    class Meta:
        ordering = ['-data', 'entrada']
        verbose_name = "Registro de Balanço"
        verbose_name_plural = "Registros de Balanço"

    def __str__(self):
        return f"Balanço: {self.usuario.username} - {self.data.strftime('%d/%m/%Y')} ({self.loja})"

    @property
    def horas_trabalhadas(self) -> Decimal:
        if self.entrada and self.saida:
            try:
                dt_e = datetime.datetime.combine(self.data, self.entrada)
                dt_s = datetime.datetime.combine(self.data, self.saida)
                segundos = (dt_s - dt_e).total_seconds()
                return Decimal(segundos / 3600)
            except Exception:
                pass
        return Decimal('0.0')

    @property
    def valor_receber(self) -> Decimal:
        return Decimal('80.00')

# ===================================================================
# === 3. MODELOS PARA O "MODO ESTUDO" ===
# ===================================================================
# (Modelos Materia e Nota permanecem iguais)

class Materia(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name="materias"
    )
    nome = models.CharField(max_length=100)
    professor = models.CharField(max_length=100, null=True, blank=True, verbose_name="Professor(a)")
    horario_disponivel = models.TextField(null=True, blank=True, verbose_name="Horário Disponível para Estudar")

    class Meta:
        unique_together = ('usuario', 'nome')
        ordering = ['nome']
        verbose_name = "Matéria"
        verbose_name_plural = "Matérias"

    def __str__(self):
        return self.nome

class Nota(models.Model):
    materia = models.ForeignKey(
        Materia, 
        on_delete=models.CASCADE, 
        related_name="notas"
    )
    descricao = models.CharField(max_length=100, verbose_name="Descrição (Ex: P1, Prova Mensal, Trabalho)")
    data_avaliacao = models.DateField(default=datetime.date.today, verbose_name="Data da Avaliação")
    nota_obtida = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Nota Obtida")
    nota_maxima = models.DecimalField(max_digits=5, decimal_places=2, default=10.0, verbose_name="Nota Máxima (Ex: 10.0)")

    class Meta:
        ordering = ['-data_avaliacao']
        verbose_name = "Nota"
        verbose_name_plural = "Notas"

    def __str__(self):
        return f"{self.materia.nome}: {self.nota_obtida} / {self.nota_maxima}"

    @property
    def percentual(self):
        if self.nota_maxima == 0:
            return Decimal('0.0')
        return (self.nota_obtida / self.nota_maxima) * 100