import io
import pandas as pd
from django.http import HttpResponse
from django.template.loader import get_template
from django.utils import timezone
from xhtml2pdf import pisa
from estoque.models import Estoque, ItemFaltante

# =========================================================
# 1. FUNÇÕES AUXILIARES DE FORMATAÇÃO
# =========================================================

def _get_sigla_unidade(unidade_obj):
    if not unidade_obj: return "UN"
    if hasattr(unidade_obj, 'sigla'): return unidade_obj.sigla
    return str(unidade_obj)

def _formatar_quantidade(valor, eh_usuario=False):
    if valor is None: return 0
    if eh_usuario: return int(valor)
    try:
        val_float = float(valor)
        if val_float.is_integer(): return int(val_float)
        return val_float
    except: return valor

# =========================================================
# 2. PROCESSADORES DE DADOS (EXTRAÇÃO)
# =========================================================

def _processar_item_casa(estoque_obj):
    item = estoque_obj.item_casa
    if not item: return None
    
    # Navegação: Item -> Localizacao e Item -> Comodo -> Imovel
    nome_imovel = item.comodo.imovel.nome if (item.comodo and item.comodo.imovel) else '-'
    nome_comodo = item.comodo.nome if item.comodo else '-'
    nome_local = item.localizacao.nome if item.localizacao else '-'

    return {
        'imovel': nome_imovel,
        'item': item.nome,
        'comodo': nome_comodo, # Ex: Cozinha
        'localizacao': nome_local,
        'qtd': _formatar_quantidade(item.quantidade),
        'unidade': _get_sigla_unidade(item.unidade),
        'validade': item.validade if item.validade else '-'
    }

def _processar_item_pet(estoque_obj):
    item = estoque_obj.item_pet
    if not item: return None

    nome_pet = item.pet.nome_pet if item.pet else 'Pet'

    return {
        'imovel': 'Geral',
        'item': item.nome,
        'comodo': nome_pet, # Ex: Meg
        'localizacao': '-',
        'qtd': _formatar_quantidade(item.quantidade),
        'unidade': _get_sigla_unidade(item.unidade),
        'validade': item.validade if item.validade else '-'
    }

def _processar_item_usuario(estoque_obj):
    item = estoque_obj.item_usuario
    if not item: return None

    nome_user = item.usuario.username
    if hasattr(item.usuario, 'first_name') and item.usuario.first_name:
        nome_user = f"{item.usuario.first_name} {item.usuario.last_name}"

    return {
        'imovel': 'Geral',
        'item': item.nome,
        'comodo': nome_user, # Ex: Diego Bonani
        'localizacao': '-',
        'qtd': _formatar_quantidade(item.quantidade, eh_usuario=True),
        'unidade': 'UN',
        'validade': '-'
    }

# =========================================================
# 3. MOTOR PDF PRINCIPAL
# =========================================================

def _gerar_pdf(modulos_selecionados, filename, usuario):
    context = {
        'titulo': 'Relatório de Estoque',
        'usuario': usuario,
        'data_emissao': timezone.now(),
        'modulos': modulos_selecionados,
        'dados': {}
    }

    if 'Estoque' in modulos_selecionados:
        sub = modulos_selecionados['Estoque']
        context['dados']['estoque'] = {}

        # --- LÓGICA DE FILTRO DE SETOR ---
        # 1. Base Query (Traz tudo preparado)
        query = Estoque.objects.select_related(
            'item_casa', 'item_casa__comodo', 'item_casa__comodo__imovel', 'item_casa__localizacao', 'item_casa__unidade',
            'item_pet', 'item_pet__pet', 'item_pet__unidade',
            'item_usuario', 'item_usuario__usuario'
        )

        # 2. Aplica Filtros se "Todos" NÃO estiver marcado
        # Se 'filtro_todos' estiver na lista, ignoramos os outros filtros e pegamos tudo.
        if 'filtro_todos' not in sub:
            setores_desejados = []
            
            if 'filtro_casa' in sub:
                setores_desejados.append('CASA')
            if 'filtro_pet' in sub:
                setores_desejados.append('PET')
            if 'filtro_usuario' in sub:
                setores_desejados.append('USUARIO') # Atenção: No banco está 'USUARIO' (sem acento no SQL dump)

            # Se o usuário não marcou nada, mas clicou em gerar, assumimos tudo ou vazio?
            # Vamos assumir que se ele selecionou setores específicos, filtramos.
            if setores_desejados:
                query = query.filter(setor__in=setores_desejados)

        if 'visao_geral' in sub:
            raw_itens = query.all()
            lista_final = []
            
            for estoque in raw_itens:
                dados = None
                # O campo 'setor' no seu banco já diz o que é. Usamos ele para direcionar.
                if estoque.setor == 'CASA':
                    dados = _processar_item_casa(estoque)
                elif estoque.setor == 'PET':
                    dados = _processar_item_pet(estoque)
                elif estoque.setor == 'USUARIO':
                    dados = _processar_item_usuario(estoque)
                
                if dados:
                    lista_final.append(dados)
            
            # Ordena
            lista_final.sort(key=lambda x: (x['imovel'], x['comodo'], x['item']))
            context['dados']['estoque']['itens'] = lista_final

        # (Compras mantido igual)
        if 'lista_compras' in sub:
            try:
                context['dados']['estoque']['compras'] = ItemFaltante.objects.filter(comprado=False)
            except: 
                context['dados']['estoque']['compras'] = []

    # Geração
    template = get_template('relatorios/pdf_base.html')
    html = template.render(context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
    
    if pisa.CreatePDF(html, dest=response).err:
        return HttpResponse('Erro PDF', status=500)
    
    return response

def gerar_relatorio(modulos, formato, user):
    fname = f"Relatorio_Estoque_{timezone.localdate()}"
    if formato == 'pdf': return _gerar_pdf(modulos, fname, user)
    return HttpResponse("Formato Excel em manutenção.", status=400)