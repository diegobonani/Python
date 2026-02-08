from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.template.loader import render_to_string
from .models import Veiculo
from .forms import VeiculoForm

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils import timezone
from .models import Veiculo, Manutencao
from .forms import VeiculoForm
# Importe os modelos de outros apps se necessário
# from deslocamento.models import Abastecimento 

@login_required
def gerenciar_veiculo(request):
    """
    View Central do Painel de Veículos.
    Carrega dados para o Dashboard, Abas e Formulário CRUD.
    """
    user = request.user
    
    # --- DADOS GERAIS ---
    veiculos = Veiculo.objects.filter(proprietario=user).order_by('-id')
    total_veiculos = veiculos.count()
    
    # --- LÓGICA DE ALERTAS (Exemplo) ---
    # Aqui você verificaria datas de manutenção, IPVA, ou KM para troca de óleo
    alertas = []
    veiculos_precisando_atencao = 0
    
    for v in veiculos:
        # Exemplo 1: Alerta de Quilometragem Alta (Simulação de revisão)
        if v.km_atual and v.km_atual > 10000: 
            # Lógica fictícia: a cada 10k km precisa de revisão
            if int(v.km_atual) % 10000 < 500: # Está próximo de um múltiplo de 10k
                alertas.append({
                    'veiculo': v,
                    'tipo': 'warning', # warning, danger, info
                    'mensagem': f'O veículo {v.modelo} está com {v.km_atual}km. Verifique a revisão de 10k.'
                })
                veiculos_precisando_atencao += 1
        
        # Exemplo 2: Alerta de Documentação (Se houver campo no model)
        # if v.data_ipva < timezone.now().date(): ...

    status_frota = "Operacional" if veiculos_precisando_atencao == 0 else "Requer Atenção"

    # --- CONTEXTO ---
    context = {
        'titulo': 'Gerenciar Veículos',
        'veiculos': veiculos,
        'form': VeiculoForm(), # Formulário para a aba "Meus Veículos"
        
        # Dados do Dashboard
        'total_veiculos': total_veiculos,
        'alertas': alertas,
        'status_frota': status_frota,
        'veiculos_atencao': veiculos_precisando_atencao,
    }
    
    return render(request, 'carro/gerenciar_veiculo.html', context)

@login_required
def salvar_veiculo(request):
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        veiculo_id = request.POST.get('veiculo_id')
        veiculo = get_object_or_404(Veiculo, pk=veiculo_id, proprietario=request.user) if veiculo_id else None
        
        form = VeiculoForm(request.POST, instance=veiculo)
        
        if form.is_valid():
            novo_veiculo = form.save(commit=False)
            novo_veiculo.proprietario = request.user
            novo_veiculo.save()
            form.save_m2m() # Salva campos ManyToMany
            
            # Renderiza apenas o partial da tabela com a lista atualizada
            veiculos = Veiculo.objects.filter(proprietario=request.user).order_by('-id')
            html = render_to_string('partials/_tabela_veiculos.html', {'veiculos': veiculos}, request=request)
            
            return JsonResponse({'status': 'ok', 'message': 'Veículo salvo com sucesso!', 'html_tabela': html})
        else:
            return JsonResponse({'status': 'error', 'errors': form.errors})
            
    return JsonResponse({'status': 'error', 'message': 'Requisição inválida'})

@login_required
def excluir_veiculo(request, veiculo_id):
    if request.method == 'POST':
        veiculo = get_object_or_404(Veiculo, pk=veiculo_id, proprietario=request.user)
        veiculo.delete()
        
        veiculos = Veiculo.objects.filter(proprietario=request.user).order_by('-id')
        html = render_to_string('partials/_tabela_veiculos.html', {'veiculos': veiculos}, request=request)
        
        return JsonResponse({'status': 'ok', 'message': 'Veículo excluído com sucesso!', 'html_tabela': html})
    return JsonResponse({'status': 'error'})

@login_required
def obter_veiculo(request, veiculo_id):
    veiculo = get_object_or_404(Veiculo, pk=veiculo_id, proprietario=request.user)
    data = {
        'id': veiculo.id,
        'nome': veiculo.nome,
        'marca': veiculo.marca,
        'modelo': veiculo.modelo,
        'placa': veiculo.placa,
        'ano': veiculo.ano,
        'consumo_cidade_gasolina': veiculo.consumo_cidade_gasolina,
        'consumo_estrada_gasolina': veiculo.consumo_estrada_gasolina,
        'consumo_cidade_etanol': veiculo.consumo_cidade_etanol,
        'consumo_estrada_etanol': veiculo.consumo_estrada_etanol,
    }
    return JsonResponse(data)