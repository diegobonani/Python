from django.shortcuts import render, redirect  # <--- Adicionado render e redirect
from django.contrib import messages            # <--- Adicionado messages
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from .models import Comodo, Localizacao
from .export_engine import gerar_relatorio # <--- Importe o motor!

# ===================================================================
# 1. FUNÇÕES AJAX EXISTENTES (Mantidas)
# ===================================================================

@login_required
def carregar_comodos_ajax(request):
    setor_id = request.GET.get('setor_id')
    if not setor_id:
        return JsonResponse([], safe=False)
    
    # Busca cômodos filtrados pelo ID do Setor
    comodos = Comodo.objects.filter(setor_id=setor_id).values('id', 'nome').order_by('nome')
    return JsonResponse(list(comodos), safe=False)

@login_required
def carregar_localizacoes_ajax(request):
    comodo_id = request.GET.get('comodo_id')
    if not comodo_id:
        return JsonResponse([], safe=False)
        
    # Busca localizações filtradas pelo ID do Cômodo
    locais = Localizacao.objects.filter(comodo_id=comodo_id).values('id', 'nome').order_by('nome')
    return JsonResponse(list(locais), safe=False)

# ===================================================================
# 2. NOVAS FUNÇÕES DE EXPORTAÇÃO GLOBAL
# ===================================================================

@login_required
def exportacao_modal_view(request):
    """
    Renderiza o modal (janela) de exportação.
    """
    # Dados de exemplo para o template não quebrar
    context = {
        'config_global': {
            'ativo': False,
            'caminho': '',
            'ultima_execucao': 'Nunca'
        }
    }
    # Certifique-se de que o arquivo HTML existe em:
    # templates/partials/_aba_exportacoes.html
    return render(request, 'partials/_aba_exportacoes.html', context)

@login_required
def processar_exportacao_global(request):
    if request.method == 'POST':
        formato = request.POST.get('formato')
        
        # Mapeamento (Igual fizemos antes)
        mapa_modulos = {
            'dados_alimentacao': 'Alimentação',
            'dados_deslocamento': 'Deslocamento',
            'dados_estoque': 'Estoque',
            'dados_estudos': 'Estudos',
            'dados_financas': 'Finanças',
            'dados_jornada': 'Jornadas',
            'dados_lavanderia': 'Lavanderia',
            'dados_rede': 'Rede',
            'dados_rotinas': 'Rotinas',
            'dados_veiculos': 'Veículos'
        }

        modulos_selecionados = {}
        for chave_html, nome_legivel in mapa_modulos.items():
            opcoes = request.POST.getlist(chave_html)
            if opcoes:
                modulos_selecionados[nome_legivel] = opcoes

        # SE O USUÁRIO SELECIONOU ALGO:
        if modulos_selecionados:
            try:
                # =======================================================
                # A MÁGICA ACONTECE AQUI:
                # Chamamos o motor e retornamos o ARQUIVO direto.
                # O navegador vai abrir a janelinha de "Salvar Como".
                # =======================================================
                return gerar_relatorio(modulos_selecionados, formato, request.user)
            
            except Exception as e:
                print(f"Erro na exportação: {e}")
                messages.error(request, f"Erro ao gerar arquivo: {e}")
        else:
            messages.warning(request, "Nenhum módulo selecionado.")
            
        return redirect(request.META.get('HTTP_REFERER', '/'))
    
    return redirect('/')

@login_required
def salvar_config_global(request):
    """
    Salva as configurações de automação (00:00).
    """
    if request.method == 'POST':
        caminho = request.POST.get('caminho')
        # Aqui depois vamos salvar no Banco de Dados
        messages.success(request, f"Caminho da nuvem atualizado (Simulação): {caminho}")
        return redirect(request.META.get('HTTP_REFERER', '/'))
    
    return redirect('/')