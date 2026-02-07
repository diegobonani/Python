# estudos/utils.py

from datetime import date

def get_status_escolar_atual():
    """
    Retorna um dicionário com o estado atual do ano letivo
    baseado na data de hoje.
    """
    hoje = date.today()
    mes = hoje.month
    dia = hoje.day

    status = {
        'trimestre_atual': 1, # Valor padrão para evitar erros
        'em_ferias': False,
        'mensagem': "",
        'fase_recuperacao': False
    }

    # --- LÓGICA DE FÉRIAS E TRIMESTRES ---
    
    # 1. JANEIRO: Férias de Verão
    if mes == 1:
        status['em_ferias'] = True
        status['trimestre_atual'] = None
        status['mensagem'] = "Férias de Verão! Aproveite para descansar."
        return status

    # 2. FEVEREIRO A ABRIL: 1º Trimestre
    elif mes in [2, 3, 4]:
        status['trimestre_atual'] = 1
        status['mensagem'] = "1º Trimestre em andamento."

    # 3. MAIO A AGOSTO: 2º Trimestre (Com pausa em Julho)
    elif mes in [5, 6, 7, 8]:
        # Férias de Julho (Simples: Mês 7 inteiro ou ajustar datas)
        if mes == 7:
            status['em_ferias'] = True
            status['trimestre_atual'] = 2
            status['mensagem'] = "Recesso Escolar de Julho."
            return status
            
        status['trimestre_atual'] = 2
        status['mensagem'] = "2º Trimestre em andamento."

    # 4. SETEMBRO A NOVEMBRO: 3º Trimestre
    elif mes in [9, 10, 11]:
        status['trimestre_atual'] = 3
        status['mensagem'] = "Reta Final: 3º Trimestre."

    # 5. DEZEMBRO: Recuperação ou Férias
    elif mes == 12:
        if dia < 20:
            status['trimestre_atual'] = 3
            status['fase_recuperacao'] = True
            status['mensagem'] = "Semana de Provas Finais / Recuperação."
        else:
            status['em_ferias'] = True
            status['trimestre_atual'] = None
            status['mensagem'] = "Férias de Fim de Ano! Boas festas!"

    return status