import requests
from bs4 import BeautifulSoup
import re
from decimal import Decimal

def limpar_valor(valor_str):
    """
    Converte strings como 'R$ 5,90' ou '5,90' para float 5.90.
    Retorna 0.0 se falhar.
    """
    if not valor_str:
        return 0.0
    # Remove R$, espaços e troca vírgula por ponto
    limpo = valor_str.replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
    try:
        return float(limpo)
    except ValueError:
        return 0.0

def importar_nota_sp(url):
    """
    Recebe a URL do QR Code (NFC-e SP) e retorna uma lista de itens raspados do HTML.
    """
    # Header é OBRIGATÓRIO para a SEFAZ não bloquear o script
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        # Tenta acessar a URL
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() 
    except requests.exceptions.RequestException as e:
        return {'sucesso': False, 'erro': f"Erro ao acessar site da Fazenda: {str(e)}"}

    soup = BeautifulSoup(response.content, 'html.parser')
    
    produtos = []

    # Estratégia: A SEFAZ SP geralmente coloca os itens em linhas <tr> com id="Item + numero"
    tabela_itens = soup.find_all('tr', id=lambda x: x and x.startswith('Item'))

    if not tabela_itens:
        # Tenta estratégia alternativa (buscando pela classe de dados do produto)
        # Às vezes o layout muda para mobile
        tabela_itens = soup.find_all('td', class_='fixo-prod-serv-descricao')
        if not tabela_itens:
             return {'sucesso': False, 'erro': "Não foi possível ler os itens. O layout da nota pode ter mudado ou o link expirou."}

    for linha in tabela_itens:
        try:
            # Se for a estrutura de TR (Tabela Desktop)
            if linha.name == 'tr':
                # Nome do produto
                nome_tag = linha.find('span', class_='txtTit')
                nome = nome_tag.text.strip() if nome_tag else "Item Desconhecido"
                
                # Código
                cod_tag = linha.find('span', class_='RCod')
                codigo = cod_tag.text.replace('(Código: ', '').replace(')', '').strip() if cod_tag else ""
                
                # Quantidade
                qtd_tag = linha.find('span', class_='Rqtd')
                qtd_texto = qtd_tag.text.replace('Qtde.:', '') if qtd_tag else "1"
                qtd = limpar_valor(qtd_texto)
                
                # Unidade
                un_tag = linha.find('span', class_='RUN')
                unidade = un_tag.text.replace('UN: ', '').strip() if un_tag else "UN"
                
                # Valor Unitário
                vl_unit_tag = linha.find('span', class_='RvlUnit')
                preco_unit_texto = vl_unit_tag.text.replace('Vl. Unit.:', '') if vl_unit_tag else "0"
                preco_unit = limpar_valor(preco_unit_texto)
                
                # Valor Total do Item
                vl_total_tag = linha.find('span', class_='valor')
                preco_total = limpar_valor(vl_total_tag.text) if vl_total_tag else 0.0

                produtos.append({
                    'nome': nome,
                    'codigo': codigo,
                    'quantidade': qtd,
                    'unidade': unidade,
                    'preco_unitario': preco_unit,
                    'preco_total': preco_total
                })
        except AttributeError:
            continue 

    # Tenta pegar nome do Mercado
    try:
        mercado = soup.find('div', class_='txtTopo').text.strip()
    except:
        mercado = "Mercado Desconhecido"

    if not produtos:
         return {'sucesso': False, 'erro': "Nenhum produto encontrado na nota."}

    return {
        'sucesso': True,
        'mercado': mercado,
        'itens': produtos
    }