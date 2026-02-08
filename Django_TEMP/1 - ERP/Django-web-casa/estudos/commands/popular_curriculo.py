from django.core.management.base import BaseCommand
from estudos.models import Disciplina, GradeCurricular, TopicoConteudo, NivelEnsino

class Command(BaseCommand):
    help = 'Popula o banco de dados com Disciplinas e BNCC (Padrão SED - 4 Bimestres)'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING("--- Iniciando Carga da BNCC (Padrão SP/SED) ---"))

        # =========================================================================
        # 1. CRIAR AS DISCIPLINAS (Ajustado para ESCOLA)
        # =========================================================================
        disciplinas_data = [
            # Nome, Categoria, Cor Hex, Meta Nota
            ("Língua Portuguesa", "ESCOLA", "#4e73df", 6.0),  # Azul
            ("Matemática",        "ESCOLA", "#e74a3b", 6.0),  # Vermelho
            ("Ciências",          "ESCOLA", "#1cc88a", 6.0),  # Verde
            ("História",          "ESCOLA", "#f6c23e", 6.0),  # Amarelo
            ("Geografia",         "ESCOLA", "#36b9cc", 6.0),  # Ciano
            ("Inglês",            "ESCOLA", "#6f42c1", 6.0),  # Roxo (Agora é ESCOLA)
            ("Artes",             "ESCOLA", "#e83e8c", 6.0),  # Rosa (Agora é ESCOLA)
            ("Educação Física",   "ESCOLA", "#858796", 6.0),  # Cinza (Agora é ESCOLA)
            # Médio / Fundamental II
            ("Física",            "ESCOLA", "#fd7e14", 6.0),  
            ("Química",           "ESCOLA", "#20c9a6", 6.0),  
            ("Biologia",          "ESCOLA", "#198754", 6.0),  
            ("Projeto de Vida",   "ESCOLA", "#2c9faf", 6.0), # Comum no novo ensino médio
            ("Tecnologia",        "ESCOLA", "#5a5c69", 6.0), # Inova Educação
        ]

        objetos_disciplina = {}

        for nome, cat, cor, meta in disciplinas_data:
            # get_or_create evita duplicidade
            obj, created = Disciplina.objects.get_or_create(
                nome=nome,
                defaults={
                    'categoria': cat,
                    'cor_etiqueta': cor,
                    'meta_nota': meta,
                    'usuario': None  # Disciplina Global
                }
            )
            # Se já existir, forçamos a atualização da categoria para ESCOLA
            if not created and obj.categoria != cat:
                obj.categoria = cat
                obj.save()
                
            objetos_disciplina[nome] = obj
            if created:
                self.stdout.write(f"Criado: {nome}")

        # =========================================================================
        # FUNÇÃO AUXILIAR (BIMESTRES)
        # =========================================================================
        def add_bncc(disc_nome, nivel_enum, ano, bimestre, topicos):
            """
            Cria a Grade Curricular e os Tópicos para um Bimestre específico
            """
            disc = objetos_disciplina.get(disc_nome)
            if not disc: return

            # Cria ou Pega a Grade (Ex: Matemática - 3º Ano)
            grade, _ = GradeCurricular.objects.get_or_create(
                disciplina=disc,
                nivel=nivel_enum,
                ano_serie=ano
            )

            # Cria os tópicos
            ordem_inicial = 1
            for nome_topico in topicos:
                TopicoConteudo.objects.get_or_create(
                    grade=grade,
                    nome=nome_topico,
                    trimestre=bimestre, # O campo chama 'trimestre' no model, mas armazena o nº do bimestre (1 a 4)
                    defaults={'ordem': ordem_inicial}
                )
                ordem_inicial += 1
            
            self.stdout.write(f" -> {disc_nome} {ano}º Ano | {bimestre}º Bimestre OK.")

        # =========================================================================
        # 2. CONTEÚDO 3º ANO FUNDAMENTAL (ELLOA) - 4 BIMESTRES
        # =========================================================================
        self.stdout.write("\n--- Processando 3º Ano (4 Bimestres) ---")

        # --- PORTUGUÊS ---
        add_bncc("Língua Portuguesa", NivelEnsino.FUND_1, 3, 1, [
            "Alfabeto e Ordem Alfabética",
            "Separação de Sílabas",
            "Sílabas Complexas (NH, LH, CH)",
            "Leitura de Cantigas e Poemas"
        ])
        add_bncc("Língua Portuguesa", NivelEnsino.FUND_1, 3, 2, [
            "Substantivos Próprios e Comuns",
            "Singular e Plural",
            "Sinais de Pontuação (. ? !)",
            "Produção de Bilhetes"
        ])
        add_bncc("Língua Portuguesa", NivelEnsino.FUND_1, 3, 3, [
            "Masculino e Feminino",
            "Sinônimos e Antônimos",
            "Ortografia: R e RR, S e SS",
            "Interpretação de Texto Informativo"
        ])
        add_bncc("Língua Portuguesa", NivelEnsino.FUND_1, 3, 4, [
            "Verbos (Ação)",
            "Adjetivos (Qualidades)",
            "Uso do M antes de P e B",
            "Produção de Pequenas Histórias"
        ])

        # --- MATEMÁTICA ---
        add_bncc("Matemática", NivelEnsino.FUND_1, 3, 1, [
            "Números até 1000",
            "Antecessor e Sucessor",
            "Adição e Subtração Simples",
            "Problemas de Lógica"
        ])
        add_bncc("Matemática", NivelEnsino.FUND_1, 3, 2, [
            "Adição com Reserva (Vai um)",
            "Subtração com Recurso (Empresta)",
            "Geometria: Figuras Planas",
            "Medidas de Tempo (Relógio e Calendário)"
        ])
        add_bncc("Matemática", NivelEnsino.FUND_1, 3, 3, [
            "Ideia da Multiplicação",
            "Tabuada do 2, 3, 4 e 5",
            "Dobro e Triplo",
            "Sistema Monetário (Dinheiro)"
        ])
        add_bncc("Matemática", NivelEnsino.FUND_1, 3, 4, [
            "Ideia da Divisão",
            "Metade e Terça Parte",
            "Medidas de Comprimento (cm, m)",
            "Leitura de Gráficos Simples"
        ])

        # --- OUTRAS MATÉRIAS (Resumido por Semestre p/ preencher Bimesters) ---
        add_bncc("Ciências", NivelEnsino.FUND_1, 3, 1, ["Os Animais e seus Ambientes"])
        add_bncc("Ciências", NivelEnsino.FUND_1, 3, 2, ["Corpo Humano e Saúde"])
        add_bncc("Ciências", NivelEnsino.FUND_1, 3, 3, ["As Plantas: Partes e Frutos"])
        add_bncc("Ciências", NivelEnsino.FUND_1, 3, 4, ["O Solo e a Água"])

        add_bncc("História", NivelEnsino.FUND_1, 3, 1, ["O Eu e o Outro (Identidade)"])
        add_bncc("História", NivelEnsino.FUND_1, 3, 2, ["A Cidade e o Município"])
        add_bncc("História", NivelEnsino.FUND_1, 3, 3, ["Espaços Públicos e Privados"])
        add_bncc("História", NivelEnsino.FUND_1, 3, 4, ["Memória e Patrimônio Cultural"])

        add_bncc("Geografia", NivelEnsino.FUND_1, 3, 1, ["Paisagem Natural e Cultural"])
        add_bncc("Geografia", NivelEnsino.FUND_1, 3, 2, ["A Vida no Campo e na Cidade"])
        add_bncc("Geografia", NivelEnsino.FUND_1, 3, 3, ["Meios de Transporte"])
        add_bncc("Geografia", NivelEnsino.FUND_1, 3, 4, ["Meios de Comunicação"])

        add_bncc("Inglês", NivelEnsino.FUND_1, 3, 1, ["Greetings (Cumprimentos)", "Colors (Cores)"])
        add_bncc("Inglês", NivelEnsino.FUND_1, 3, 2, ["Numbers 1-20", "Family Members"])
        add_bncc("Inglês", NivelEnsino.FUND_1, 3, 3, ["Animals", "Body Parts"])
        add_bncc("Inglês", NivelEnsino.FUND_1, 3, 4, ["Foods", "School Objects"])

        # =========================================================================
        # 3. EXEMPLO FUNDAMENTAL II (9º ANO)
        # =========================================================================
        self.stdout.write("\n--- Processando 9º Ano ---")
        add_bncc("Física", NivelEnsino.FUND_2, 9, 1, ["Cinemática", "Movimento Uniforme"])
        add_bncc("Física", NivelEnsino.FUND_2, 9, 2, ["Força e Leis de Newton"])
        add_bncc("Química", NivelEnsino.FUND_2, 9, 1, ["Matéria e Energia", "Estados Físicos"])
        add_bncc("Química", NivelEnsino.FUND_2, 9, 2, ["Tabela Periódica"])

        self.stdout.write(self.style.SUCCESS('\n--- Sucesso! Currículo 4 Bimestres Carregado. ---'))