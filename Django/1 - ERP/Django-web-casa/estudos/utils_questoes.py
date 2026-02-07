import random

# BANCO DE QUESTÕES INTELIGENTE (TI & IDIOMAS)
BANCO_QUESTOES = {
    # --- TI / PROGRAMAÇÃO ---
    'logica': [
        "O que é um algoritmo? Dê um exemplo do dia a dia.",
        "Explique o que é uma variável e para que serve.",
        "Qual a diferença entre dados do tipo Inteiro e String?",
        "O que acontece se tentarmos somar o texto '10' com o número 10?",
        "Desenhe o fluxograma de um sistema que pede senha ao usuário."
    ],
    'variavel': [ # Pega "variaveis", "variável"
        "Declare uma variável em Python que guarde seu nome.",
        "Quais são os principais tipos de dados primitivos?",
        "O que significa 'tipagem dinâmica'?",
        "Qual a diferença entre = (atribuição) e == (comparação)?",
        "Como converter um número texto '5' para um número inteiro?"
    ],
    'condicional': [ # Pega "if", "else", "condicionais"
        "Para que serve o comando IF?",
        "Escreva um código que verifique se uma pessoa é maior de idade.",
        "O que é um ELIF?",
        "Explique a tabela verdade do operador AND e OR.",
        "O que acontece se nenhuma condição do IF for verdadeira?"
    ],
    'loop': [ # Pega "for", "while", "repetição"
        "Qual a diferença entre FOR e WHILE?",
        "O que é um loop infinito? Como evitar?",
        "Escreva um loop que conte de 1 até 10.",
        "Para que serve o comando 'break'?",
        "Como percorrer uma lista de nomes usando um loop?"
    ],
    'funcao': [ # Pega "funções", "def", "métodos"
        "O que é uma função e por que devemos usá-la?",
        "O que é um parâmetro/argumento?",
        "O que faz a palavra reservada 'return'?",
        "Qual a diferença entre escopo global e local?",
        "Crie uma função que receba dois números e retorne a soma."
    ],
    'array': [ # Pega "listas", "vetores", "coleções"
        "O que é um Array (ou Lista)?",
        "Como acessar o primeiro item de uma lista?",
        "Como adicionar um item novo ao final de uma lista?",
        "Qual o índice do terceiro elemento de uma lista?",
        "Como descobrir o tamanho total de uma lista?"
    ],

    # --- IDIOMAS (INGLÊS) ---
    'verb to be': [
        "Conjugue o verbo To Be no presente (I, You, He/She/It...)",
        "Traduza: 'She is my sister'.",
        "Como transformar a frase 'He is happy' em uma pergunta?",
        "Qual a forma negativa de 'They are students'?",
        "Complete: I ___ a student."
    ],
    'present simple': [
        "Quando usamos o Present Simple?",
        "Como fica o verbo 'Work' para 'She'? (She works...)",
        "Traduza: 'I do not like coffee'.",
        "Crie uma frase usando 'Always' (Sempre).",
        "Como perguntar 'Você mora aqui?' em inglês?"
    ],
    'colors': [
        "Escreva o nome de 5 cores em inglês.",
        "Que cor é 'Purple'?",
        "Traduza: 'The sky is blue'.",
        "Qual a cor do sol em inglês?",
        "Como se escreve 'Preto e Branco'?"
    ]
}

def gerar_questoes_por_topico(titulo_prova):
    """
    Analisa o título digitado e retorna questões pertinentes.
    """
    titulo = titulo_prova.lower()
    questoes_selecionadas = []
    
    # Varre o banco procurando palavras-chave no título
    encontrou_tema = False
    
    for chave, perguntas in BANCO_QUESTOES.items():
        # Verifica se a chave (ex: 'variavel') está no título (ex: 'Prova de Variáveis')
        # Removemos o 's' final para pegar plurais simples
        chave_simples = chave[:-1] if chave.endswith('s') else chave
        
        if chave_simples in titulo:
            encontrou_tema = True
            # Seleciona 3 perguntas aleatórias desse tema
            questoes_selecionadas.extend(random.sample(perguntas, min(3, len(perguntas))))

    if not encontrou_tema:
        return [
            "1. Descreva com suas palavras o que você aprendeu neste módulo.",
            "2. Cite 3 exemplos práticos do conteúdo estudado.",
            "3. Qual foi a parte mais difícil deste tópico para você?",
            "4. (O sistema não identificou o tema específico no título. Tente usar palavras como 'Variáveis', 'Loop', 'Verbo To Be' no título)."
        ]

    # Embaralha e formata
    random.shuffle(questoes_selecionadas)
    
    # Formata como texto para o textarea
    texto_final = ""
    for i, q in enumerate(questoes_selecionadas, 1):
        texto_final += f"{i}. {q}\n"
        
    return texto_final