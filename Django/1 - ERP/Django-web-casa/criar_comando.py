import os

# Conteúdo do comando popular_curriculo
CODIGO_COMANDO = """from django.core.management.base import BaseCommand
from estudos.models import Disciplina, GradeCurricular, TopicoConteudo, NivelEnsino

class Command(BaseCommand):
    help = 'Popula o banco de dados com Disciplinas e BNCC'

    def handle(self, *args, **kwargs):
        self.stdout.write("--- Iniciando Carga da BNCC ---")

        # 1. DISCIPLINAS BÁSICAS
        disciplinas_data = [
            ("Língua Portuguesa", "ESCOLA", "#4e73df", 6.0),
            ("Matemática",        "ESCOLA", "#e74a3b", 6.0),
            ("Ciências",          "ESCOLA", "#1cc88a", 6.0),
            ("História",          "ESCOLA", "#f6c23e", 6.0),
            ("Geografia",         "ESCOLA", "#36b9cc", 6.0),
            ("Inglês",            "IDIOMA", "#6f42c1", 7.0),
            ("Artes",             "ARTE",   "#e83e8c", 6.0),
            ("Educação Física",   "ARTE",   "#858796", 6.0),
            ("Física",            "ESCOLA", "#fd7e14", 6.0),
            ("Química",           "ESCOLA", "#20c9a6", 6.0),
            ("Biologia",          "ESCOLA", "#198754", 6.0),
        ]

        objetos_disciplina = {}

        for nome, cat, cor, meta in disciplinas_data:
            obj, created = Disciplina.objects.get_or_create(
                nome=nome,
                defaults={'categoria': cat, 'cor_etiqueta': cor, 'meta_nota': meta}
            )
            objetos_disciplina[nome] = obj
            print(f"Disciplina: {nome}")

        # 2. POPULAR CONTEÚDO (BNCC)
        def add_bncc(disc_nome, nivel_enum, ano, trimestre, topicos):
            disc = objetos_disciplina.get(disc_nome)
            if not disc: return
            
            grade, _ = GradeCurricular.objects.get_or_create(
                disciplina=disc, nivel=nivel_enum, ano_serie=ano
            )
            
            ordem = 1
            for t in topicos:
                TopicoConteudo.objects.get_or_create(
                    grade=grade, nome=t, trimestre=trimestre, defaults={'ordem': ordem}
                )
                ordem += 1
            print(f" -> BNCC {disc_nome} {ano}º Ano - Tri {trimestre} OK.")

        # --- CONTEÚDO 3º ANO (ELLOA) ---
        add_bncc("Língua Portuguesa", NivelEnsino.FUND_1, 3, 1, [
            "Leitura e compreensão de textos curtos", "Sílabas complexas (LH, NH, CH)", 
            "Separação silábica", "Uso de Letra Maiúscula"
        ])
        add_bncc("Matemática", NivelEnsino.FUND_1, 3, 1, [
            "Números até 1000", "Adição com Reserva", "Subtração com Recurso", "Problemas Simples"
        ])
        
        # --- EXEMPLOS FUND. II ---
        add_bncc("Física", NivelEnsino.FUND_2, 9, 1, ["Cinemática", "Leis de Newton"])

        self.stdout.write("--- SUCESSO! ---")
"""

def criar_estrutura():
    base_path = os.path.join('estudos', 'management', 'commands')
    
    # 1. Cria as pastas se não existirem
    if not os.path.exists(base_path):
        os.makedirs(base_path)
        print(f"Pastas criadas: {base_path}")

    # 2. Cria os arquivos __init__.py (OBRIGATÓRIOS)
    init_1 = os.path.join('estudos', 'management', '__init__.py')
    init_2 = os.path.join('estudos', 'management', 'commands', '__init__.py')
    
    with open(init_1, 'w') as f: pass
    with open(init_2, 'w') as f: pass
    print("Arquivos __init__.py criados.")

    # 3. Cria o arquivo do comando
    arquivo_comando = os.path.join(base_path, 'popular_curriculo.py')
    with open(arquivo_comando, 'w', encoding='utf-8') as f:
        f.write(CODIGO_COMANDO)
    
    print(f"Arquivo 'popular_curriculo.py' criado com sucesso!")
    print("Agora você pode rodar: python manage.py popular_curriculo")

if __name__ == '__main__':
    criar_estrutura()