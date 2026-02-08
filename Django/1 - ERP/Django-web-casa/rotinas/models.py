from django.db import models
from django.conf import settings
from django.utils import timezone

# ==============================================================================
# 1. MOLDE DA ROTINA (O que deve ser feito?)
# ==============================================================================
class RotinaPadrao(models.Model):
    """ 
    Define o modelo da tarefa. Ex: 'Lavar a Louça'.
    """
    nome = models.CharField(max_length=200, verbose_name="Nome da Rotina")
    descricao = models.TextField(blank=True, verbose_name="Diretriz / Instrução")
    pontuacao_base = models.IntegerField(default=10, verbose_name="Pontos Base")
    horario_sugerido = models.TimeField(null=True, blank=True, verbose_name="Horário Sugerido")
    
    # Recorrência: 'ALL' (Todos os dias) ou '0,2,4' (Seg, Qua, Sex)
    dias_recorrencia = models.CharField(max_length=50, default='ALL', help_text="Ex: 'ALL' ou '0,1,2,3,4' (0=Segunda)")
    
    ativa = models.BooleanField(default=True)

    # Define quais usuários geralmente recebem essa tarefa
    usuarios_padrao = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        blank=True, 
        related_name='rotinas_padrao_atribuidas'
    )

    def __str__(self):
        return f"{self.nome} ({self.pontuacao_base} pts)"

# ==============================================================================
# 2. TAREFA DIÁRIA (A execução real)
# ==============================================================================
class TarefaDiaria(models.Model):
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('CONCLUIDO', 'Concluído'),
        ('NAO_FEITO', 'Não Realizado/Falhou'),
    ]

    rotina = models.ForeignKey(RotinaPadrao, on_delete=models.CASCADE)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    data_tarefa = models.DateField(default=timezone.now, verbose_name="Data da Atribuição")
    prazo_hora = models.TimeField(null=True, blank=True, verbose_name="Prazo Final")
    data_conclusao = models.DateTimeField(null=True, blank=True)

    prazo_final = models.DateTimeField(null=True, blank=True, verbose_name="Prazo Absoluto")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE')
    
    pontos_ganhos = models.IntegerField(default=0, verbose_name="Total de Pontos")
    pontos_extra = models.IntegerField(default=0, verbose_name="Bônus/Penalidade Extra")
    
    observacao_admin = models.TextField(blank=True, null=True, verbose_name="Feedback do Admin")

    class Meta:
        unique_together = ('rotina', 'usuario', 'data_tarefa')
        ordering = ['status', 'prazo_hora']

    def save(self, *args, **kwargs):
        # Lógica Automática de Pontuação
        if self.status == 'CONCLUIDO':
            self.pontos_ganhos = self.rotina.pontuacao_base + self.pontos_extra
        elif self.status == 'NAO_FEITO':
            self.pontos_ganhos = 0 
        else:
            self.pontos_ganhos = 0 
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.usuario.username} - {self.rotina.nome} - {self.get_status_display()}"

# ==============================================================================
# 3. SISTEMA DE DISCIPLINA
# ==============================================================================
class HistoricoCastigo(models.Model):
    GRAVIDADE_CHOICES = [
        ('LEVE', 'Leve (Atenção)'),
        ('MEDIA', 'Média (Advertência)'),
        ('GRAVE', 'Grave (Disciplina)'),
        ('GRAVISSIMA', 'Gravíssima (Suspensão)'),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='historico_castigos'
    )
    aplicado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    data_ocorrencia = models.DateTimeField(default=timezone.now)
    motivo = models.CharField(max_length=255)
    descricao_detalhada = models.TextField(blank=True)
    gravidade = models.CharField(max_length=20, choices=GRAVIDADE_CHOICES, default='MEDIA')
    
    pontos_perdidos = models.IntegerField()
    
    cumprido = models.BooleanField(default=False, verbose_name="Castigo Finalizado?")
    data_liberacao = models.DateField(null=True, blank=True)

    def save(self, *args, **kwargs):
        # Garante valor negativo
        if self.pontos_perdidos > 0:
            self.pontos_perdidos = self.pontos_perdidos * -1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Castigo: {self.usuario.username} | {self.pontos_perdidos}"

# ==============================================================================
# 4. FECHAMENTO MENSAL
# ==============================================================================
class FechamentoMensal(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    mes = models.IntegerField()
    ano = models.IntegerField()
    
    total_tarefas = models.IntegerField(default=0)
    total_castigos = models.IntegerField(default=0)
    ajuste_admin = models.IntegerField(default=0)
    saldo_final = models.IntegerField(default=0)
    
    lancado = models.BooleanField(default=False)
    data_lancamento = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('usuario', 'mes', 'ano')

    def save(self, *args, **kwargs):
        self.saldo_final = self.total_tarefas + self.total_castigos + self.ajuste_admin
        super().save(*args, **kwargs)