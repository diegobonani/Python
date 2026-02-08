import os
from django.db import models
from django.conf import settings
from django.utils import timezone
from usuarios.models import Perfil 

# =============================================================================
# FUNÇÃO AUXILIAR DE CAMINHO
# =============================================================================
def caminho_arquivo_aula(instance, filename):
    """
    Organiza os uploads em pastas: catalogo/Curso/Modulo/arquivo.mp4
    """
    try:
        curso_nome = instance.modulo.curso.titulo
        modulo_nome = instance.modulo.titulo
        # Limpa caracteres especiais para evitar erro no sistema de arquivos
        return os.path.join('catalogo', curso_nome, modulo_nome, filename)
    except:
        return os.path.join('catalogo', 'uploads_gerais', filename)


# =============================================================================
# 1. O ACERVO (NETFLIX / CATALOGO)
# =============================================================================

class AreaConhecimento(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    icone = models.CharField(max_length=50, default="fas fa-layer-group", help_text="Classe FontAwesome (ex: fas fa-code)")
    cor_identidade = models.CharField(max_length=7, default="#4e73df", help_text="Cor Hex (ex: #FF0000)")

    def __str__(self): return self.nome
    
    class Meta:
        verbose_name = "1. Área de Conhecimento"
        verbose_name_plural = "1. Áreas de Conhecimento"
        ordering = ['nome']

class Especialidade(models.Model):
    area = models.ForeignKey(AreaConhecimento, on_delete=models.CASCADE, related_name='especialidades')
    nome = models.CharField(max_length=100)

    # __str__ hierárquico ajuda no Select2 (Ex: "TI > Desenvolvimento Web")
    def __str__(self): return f"{self.area.nome} > {self.nome}"
    
    class Meta:
        verbose_name = "2. Especialidade"
        verbose_name_plural = "2. Especialidades"
        ordering = ['area', 'nome']

class Curso(models.Model):
    especialidade = models.ForeignKey(Especialidade, on_delete=models.SET_NULL, null=True, related_name='cursos')
    titulo = models.CharField(max_length=200)
    descricao = models.TextField(blank=True, verbose_name="Sinopse")
    capa = models.ImageField(upload_to='catalogo/capas/', null=True, blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    
    def __str__(self): return self.titulo
    
    class Meta:
        verbose_name = "3. Curso"
        verbose_name_plural = "3. Cursos"
        ordering = ['titulo']

class ModuloCurso(models.Model):
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='modulos')
    titulo = models.CharField(max_length=200)
    ordem = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['ordem', 'titulo']
        verbose_name = "4. Módulo"
        verbose_name_plural = "4. Módulos"

    def __str__(self): return f"{self.curso.titulo} | {self.titulo}"

class Aula(models.Model):
    modulo = models.ForeignKey(ModuloCurso, on_delete=models.CASCADE, related_name='aulas')
    titulo = models.CharField(max_length=200)
    
    # Arquivo local (Upload direto)
    video_arquivo = models.FileField(
        upload_to=caminho_arquivo_aula, 
        max_length=500, 
        null=True, 
        blank=True, 
        help_text="Arquivo de vídeo local (.mp4)"
    )

    # Link do Telegram (tg://) ou YouTube
    # Usamos CharField porque URLField rejeita 'tg://'
    video_link = models.CharField(
        max_length=500, 
        blank=True, 
        null=True, 
        help_text="Link YouTube/Vimeo ou ID Telegram (tg://-100.../ID)"
    )
    
    duracao = models.CharField(max_length=10, blank=True, help_text="Ex: 10:30")
    ordem = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['ordem', 'titulo']
        verbose_name = "5. Aula / Vídeo"
        verbose_name_plural = "5. Aulas"

    def __str__(self): return f"{self.ordem}. {self.titulo}"
    
    @property
    def is_telegram(self):
        """Retorna True se for um vídeo do Telegram"""
        return self.video_link and str(self.video_link).startswith('tg://')


# =============================================================================
# 2. O ALUNO (MATRÍCULA & GESTÃO)
# =============================================================================

class Disciplina(models.Model):
    CATEGORIAS = [
        ('ESCOLA', '🏫 Escola (Regular/SED)'),
        ('EXTRA', '🎓 Curso Livre / Skill (Netflix)'),
        ('IDIOMA', '🗣️ Idiomas'),
        ('VESTIBULAR', '📚 Preparatório'),
    ]
    
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='disciplinas', null=True, blank=True)
    
    # Conexão com o Catálogo (Permite o Select2 funcionar)
    curso_catalogo = models.ForeignKey(Curso, on_delete=models.SET_NULL, null=True, blank=True, related_name='alunos_matriculados')
    
    nome = models.CharField(max_length=100, help_text="Nome da matéria escolar ou título do curso", blank=True)
    categoria = models.CharField(max_length=20, choices=CATEGORIAS, default='ESCOLA')
    professor = models.CharField(max_length=100, blank=True, null=True)
    meta_nota = models.DecimalField(max_digits=4, decimal_places=2, default=6.0)
    cor_etiqueta = models.CharField(max_length=7, default='#0d6efd')

    class Meta:
        verbose_name = "Minha Disciplina"
        verbose_name_plural = "6. Minhas Disciplinas"
        ordering = ['nome']

    def save(self, *args, **kwargs):
        # Automágica: Se selecionou um curso do catálogo, puxa os dados dele
        if self.curso_catalogo:
            if not self.nome: 
                self.nome = self.curso_catalogo.titulo
            self.categoria = 'EXTRA'
            
            # Tenta puxar a cor da Área de Conhecimento
            if self.curso_catalogo.especialidade and self.curso_catalogo.especialidade.area:
                self.cor_etiqueta = self.curso_catalogo.especialidade.area.cor_identidade
        
        # Fallback se não tiver nome
        if not self.nome:
            self.nome = "Nova Disciplina"
            
        super().save(*args, **kwargs)

    def __str__(self):
        user_name = self.usuario.first_name if self.usuario else "Base Comum"
        return f"{self.nome} ({user_name})"

class ProgressoAula(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    aula = models.ForeignKey(Aula, on_delete=models.CASCADE)
    concluido = models.BooleanField(default=False)
    data_conclusao = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('usuario', 'aula')
        verbose_name = "Progresso de Aula"
        verbose_name_plural = "7. Progresso dos Alunos"


# =============================================================================
# 3. PLANNER (AGENDA)
# =============================================================================
class AtividadeEstudo(models.Model):
    TIPOS = [
        ('AULA', '🏫 Aula (Presencial/Online)'),
        ('TAREFA', '🏠 Tarefa de Casa'),
        ('TRABALHO', '🎨 Trabalho / Projeto'),
        ('REVISAO', '📖 Revisão / Estudo Dirigido'),
        ('PROVA', '📝 Prova / Teste'),
    ]
    
    disciplina = models.ForeignKey(Disciplina, on_delete=models.CASCADE, related_name='atividades')
    titulo = models.CharField(max_length=200)
    tipo = models.CharField(max_length=20, choices=TIPOS)
    data_agendada = models.DateField(default=timezone.now)
    hora_inicio = models.TimeField(null=True, blank=True)
    concluido = models.BooleanField(default=False)
    data_conclusao = models.DateTimeField(null=True, blank=True)
    pontos_xp = models.IntegerField(default=10)

    class Meta:
        verbose_name = "Atividade do Planner"
        verbose_name_plural = "Atividades do Planner"
        ordering = ['data_agendada', 'hora_inicio']

    def __str__(self): return f"{self.titulo} - {self.disciplina}"

    def save(self, *args, **kwargs):
        if self.concluido and not self.data_conclusao:
            self.data_conclusao = timezone.now()
        super().save(*args, **kwargs)


# =============================================================================
# 4. SISTEMA ESCOLAR (SED / LEGADO)
# =============================================================================

class NivelEnsino(models.TextChoices):
    FUND_1 = 'F1', 'Fundamental I (1º ao 5º Ano)'
    FUND_2 = 'F2', 'Fundamental II (6º ao 9º Ano)'
    MEDIO = 'EM', 'Ensino Médio (1º ao 3º Ano)'

class GradeCurricular(models.Model):
    disciplina = models.ForeignKey(Disciplina, on_delete=models.CASCADE)
    nivel = models.CharField(max_length=2, choices=NivelEnsino.choices)
    ano_serie = models.IntegerField()
    descricao_bncc = models.TextField(blank=True) 
    
    class Meta:
        unique_together = ('disciplina', 'nivel', 'ano_serie')
        ordering = ['nivel', 'ano_serie', 'disciplina']
        verbose_name = "Grade Curricular"
        verbose_name_plural = "Grades Curriculares"
    
    def __str__(self): return f"{self.disciplina.nome} - {self.get_nivel_display()}"

class TopicoConteudo(models.Model):
    grade = models.ForeignKey(GradeCurricular, on_delete=models.CASCADE, related_name='topicos', null=True, blank=True)
    disciplina = models.ForeignKey(Disciplina, on_delete=models.CASCADE, related_name='topicos', null=True, blank=True)
    nome = models.CharField(max_length=200)
    bimestre_sugerido = models.IntegerField(default=1)
    concluido = models.BooleanField(default=False)
    nivel = models.IntegerField(default=2, choices=[(1, 'Fácil'), (2, 'Médio'), (3, 'Difícil')])
    observacao = models.TextField(blank=True)
    
    def __str__(self): return self.nome

class Matricula(models.Model):
    aluno = models.ForeignKey(Perfil, on_delete=models.CASCADE, limit_choices_to={'esta_estudando': True})
    ano_letivo = models.IntegerField(default=2026)
    ano_serie_atual = models.IntegerField()
    nivel_atual = models.CharField(max_length=2, choices=NivelEnsino.choices)
    escola_nome = models.CharField(max_length=200, default="Escola Padrão")

    class Meta:
        unique_together = ('aluno', 'ano_letivo')
        verbose_name = "Matrícula Escolar"
        verbose_name_plural = "Matrículas Escolares"

    def __str__(self): return f"{self.aluno.nome_completo} - {self.ano_serie_atual}º Ano ({self.ano_letivo})"

class DiarioBordo(models.Model):
    matricula = models.ForeignKey(Matricula, on_delete=models.CASCADE)
    disciplina_base = models.ForeignKey(Disciplina, on_delete=models.CASCADE)
    
    # Notas Bimestrais
    nota_1_bim = models.FloatField(null=True, blank=True)
    nota_2_bim = models.FloatField(null=True, blank=True)
    nota_3_bim = models.FloatField(null=True, blank=True)
    nota_4_bim = models.FloatField(null=True, blank=True)
    nota_final = models.FloatField(null=True, blank=True)
    
    total_faltas = models.IntegerField(default=0)
    
    # Flags de Dificuldade
    dificuldade_leitura = models.BooleanField(default=False)
    dificuldade_escrita = models.BooleanField(default=False)
    dificuldade_logica = models.BooleanField(default=False)
    observacao_pedagogica = models.TextField(blank=True)
    
    class Meta:
        unique_together = ('matricula', 'disciplina_base')
        verbose_name = "Diário de Bordo"
        verbose_name_plural = "Diários de Bordo"
    
    def __str__(self): return f"Diário: {self.matricula.aluno.nome_completo} - {self.disciplina_base.nome}"

class Avaliacao(models.Model):
    disciplina = models.ForeignKey(Disciplina, on_delete=models.CASCADE, related_name='avaliacoes')
    descricao = models.CharField(max_length=100)
    data = models.DateField(default=timezone.now)
    
    # Consolidado: Nota que o aluno tirou vs Nota Máxima
    nota_obtida = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True) 
    nota_maxima = models.DecimalField(max_digits=4, decimal_places=2, default=10.0)
    
    def __str__(self): return f"{self.descricao} ({self.disciplina.nome})"