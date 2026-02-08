# Em: lavanderia/views.py

import requests
import datetime
from decimal import Decimal
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string

# Imports de outros apps
from core.models import Equipamento
from estoque.models import Estoque
from core.decorators import admin_required # <-- IMPORTADO NOSSO DECORATOR DE GESTÃO

# Imports deste app
from .models import CicloLavagem, CestoDeRoupas, ProdutoConsumidoLavagem
from .forms import CestoDeRoupasForm, IniciarCicloForm, ProdutoConsumidoForm

# ===================================================================
# === FUNÇÕES AUXILIARES (HELPERS) ===
# (Não são views, não precisam de decorator)
# ===================================================================

def get_weather_forecast(latitude, longitude):
    """ Função da Previsão do Tempo """
    try:
        api_url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}"
            "&daily=weathercode,temperature_2m_max,precipitation_probability_max"
            "&timezone=America/Sao_Paulo"
        )
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        previsao_diaria = []
        dias_semana = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        weather_codes = {
            0: ("Céu Limpo", '<i class="fas fa-sun text-warning"></i>'), 1: ("Quase Limpo", '<i class="fas fa-cloud-sun text-warning"></i>'),
            2: ("Parcialmente Nublado", '<i class="fas fa-cloud text-secondary"></i>'), 3: ("Nublado", '<i class="fas fa-cloud text-secondary"></i>'),
            45: ("Nevoeiro", '<i class="fas fa-smog text-muted"></i>'), 48: ("Nevoeiro Congelante", '<i class="fas fa-smog text-info"></i>'),
            51: ("Garoa Leve", '<i class="fas fa-cloud-rain text-info"></i>'), 53: ("Garoa Moderada", '<i class="fas fa-cloud-rain text-info"></i>'),
            55: ("Garoa Forte", '<i class="fas fa-cloud-rain text-info"></i>'), 61: ("Chuva Leve", '<i class="fas fa-cloud-showers-heavy text-primary"></i>'),
            63: ("Chuva Moderada", '<i class="fas fa-cloud-showers-heavy text-primary"></i>'), 65: ("Chuva Forte", '<i class="fas fa-cloud-showers-heavy text-primary"></i>'),
            80: ("Pancadas de Chuva", '<i class="fas fa-cloud-showers-heavy text-danger"></i>'), 95: ("Trovoada", '<i class="fas fa-bolt text-danger"></i>'),
        }
        for i in range(len(data['daily']['time'])):
            data_previsao = datetime.datetime.strptime(data['daily']['time'][i], '%Y-%m-%d').date()
            dia_da_semana_num = data_previsao.weekday()
            codigo = data['daily']['weathercode'][i]
            descricao, icone = weather_codes.get(codigo, ("Desconhecido", '<i class="fas fa-question"></i>'))
            previsao_diaria.append({
                'data': data_previsao,
                'dia_semana': "Hoje" if i == 0 else "Amanhã" if i == 1 else dias_semana[dia_da_semana_num],
                'temp_max': round(data['daily']['temperature_2m_max'][i]),
                'chuva_prob': data['daily']['precipitation_probability_max'][i],
                'descricao': descricao, 'icone': icone,
            })
        return previsao_diaria
    except requests.RequestException:
        return {'erro': 'Não foi possível obter a previsão do tempo.'}

def recarregar_painel_ciclos(request):
    """
    Função auxiliar para recarregar o painel de ciclos.
    É chamada pelas views AJAX e, portanto, já está protegida.
    """
    form_cesto = CestoDeRoupasForm()
    maquina = Equipamento.objects.filter(capacidade_kg__isnull=False).first()
    capacidade_maquina = maquina.capacidade_kg if maquina else Decimal('13.0')
    
    ciclos_ativos = CicloLavagem.objects.filter(
        ~Q(status_processo='CONCLUIDO')
    ).prefetch_related('cestos', 'equipamento', 'produtoconsumidolavagem_set', 'produtoconsumidolavagem_set__produto_estoque').order_by('data_hora_inicio')

    cestos_aguardando = CestoDeRoupas.objects.filter(status='AGUARDANDO').order_by('-prioridade', 'data_adicionado')
    
    cestos_agrupados = {}
    for tipo_id, tipo_nome in CestoDeRoupas.TIPO_ROUPA_CHOICES:
        cestos_agrupados[tipo_id] = {'nome': tipo_nome, 'cestos': [], 'peso_total': Decimal('0.0'), 'percentual': 0}
        
    for cesto in cestos_aguardando:
        cestos_agrupados[cesto.tipo_roupa]['cestos'].append(cesto)
        cestos_agrupados[cesto.tipo_roupa]['peso_total'] += cesto.peso_kg
    
    melhor_sugestao = None
    maior_peso = Decimal('0.0')

    for tipo_id, dados in cestos_agrupados.items():
        if capacidade_maquina > 0:
            percentual = (dados['peso_total'] / capacidade_maquina) * 100
            dados['percentual'] = min(round(percentual), 100)
        else:
            dados['percentual'] = 0
            
        if 0 < dados['peso_total'] <= capacidade_maquina:
            if dados['peso_total'] > maior_peso:
                maior_peso = dados['peso_total']
                melhor_sugestao = dados
                melhor_sugestao['tipo_id'] = tipo_id
    
    contexto = {
        'form_cesto': form_cesto,
        'form_editar_cesto': CestoDeRoupasForm(), 
        'form_iniciar_ciclo': IniciarCicloForm(),
        'form_produto': ProdutoConsumidoForm(), 
        'ciclos_ativos': ciclos_ativos,
        'cestos_agrupados': cestos_agrupados,
        'melhor_sugestao': melhor_sugestao,
        'capacidade_maquina': capacidade_maquina,
    }
    return render(request, 'partials/_aba_ciclos_lavanderia.html', contexto)


# ===================================================================
# === 1. VIEWS DE GESTÃO (ADMINISTRADORES / SUPER USERS) ===
# (Protegidas com @admin_required)
# ===================================================================

@login_required
@admin_required # <-- PROTEGIDO
def gerenciar_lavanderia(request):
    latitude = -21.48004
    longitude = -49.2279
    previsao = get_weather_forecast(latitude, longitude)
    contexto = {'previsao_diaria': previsao}
    return render(request, 'lavanderia/gerenciar_lavanderia.html', contexto)

@login_required
@admin_required # <-- PROTEGIDO
def aba_ciclos_hoje_partial(request):
    """ View AJAX que retorna o conteúdo do 'Painel de Controle' da lavanderia. """
    if request.method == 'POST':
        form_cesto = CestoDeRoupasForm(request.POST)
        if form_cesto.is_valid():
            form_cesto.save()
            return recarregar_painel_ciclos(request)
        else:
             return recarregar_painel_ciclos(request)
    
    return recarregar_painel_ciclos(request)

@login_required
@admin_required # <-- PROTEGIDO
def aba_historico_lavanderia_partial(request):
    """ View AJAX que retorna o conteúdo da aba "Histórico". """
    data_fim_str = request.GET.get('data_fim')
    data_inicio_str = request.GET.get('data_inicio')
    data_fim = datetime.datetime.strptime(data_fim_str, '%Y-%m-%d').date() if data_fim_str else timezone.now().date()
    data_inicio = datetime.datetime.strptime(data_inicio_str, '%Y-%m-%d').date() if data_inicio_str else data_fim - datetime.timedelta(days=6)
    ciclos_concluidos = CicloLavagem.objects.filter(
        data_hora_inicio__date__range=[data_inicio, data_fim],
    ).prefetch_related('cestos__usuario').order_by('-data_hora_inicio')
    contexto = {
        'ciclos': ciclos_concluidos,
        'data_inicio': data_inicio.strftime('%Y-%m-%d'),
        'data_fim': data_fim.strftime('%Y-%m-%d'),
    }
    return render(request, 'partials/_aba_historico_lavanderia.html', contexto)

# --- VIEWS DE AÇÕES PARA CESTOS ---

@login_required
@admin_required # <-- PROTEGIDO
def cesto_detalhes_json(request, pk):
    cesto = get_object_or_404(CestoDeRoupas, pk=pk)
    data = {
        'usuario': cesto.usuario.id if cesto.usuario else "",
        'tipo_roupa': cesto.tipo_roupa,
        'quantidade_cestos': cesto.quantidade_cestos,
        'prioridade': cesto.prioridade,
    }
    return JsonResponse(data)

@login_required
@require_POST
@admin_required # <-- PROTEGIDO
def cesto_editar(request, pk):
    cesto = get_object_or_404(CestoDeRoupas, pk=pk)
    form = CestoDeRoupasForm(request.POST, instance=cesto)
    if form.is_valid():
        form.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'errors': form.errors.as_json()}, status=400)

@login_required
@require_POST
@admin_required # <-- PROTEGIDO
def cesto_excluir(request, pk):
    try:
        cesto = get_object_or_404(CestoDeRoupas, pk=pk)
        cesto.delete()
        return JsonResponse({'success': True, 'message': 'Cesto excluído com sucesso.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

# --- VIEWS DE AÇÕES PARA CICLOS (MÁQUINA VIRTUAL) ---

@login_required
@require_POST
@admin_required # <-- PROTEGIDO
def iniciar_ciclo_lavagem(request):
    form = IniciarCicloForm(request.POST)
    tipo_carga = request.POST.get('tipo_carga')

    if not tipo_carga:
        return JsonResponse({'success': False, 'message': 'Tipo de carga não especificado.'}, status=400)
    if form.is_valid():
        cestos_para_lavar = CestoDeRoupas.objects.filter(status='AGUARDANDO', tipo_roupa=tipo_carga)
        if not cestos_para_lavar.exists():
            return JsonResponse({'success': False, 'message': 'Nenhum cesto encontrado para este tipo de carga.'}, status=400)
        
        ciclo = form.save(commit=False)
        ciclo.usuario_responsavel = request.user
        ciclo.status_processo = 'LAVANDO' 
        ciclo.data_hora_inicio = timezone.now()
        ciclo.data_hora_inicio_etapa = timezone.now()
        ciclo.save() 
        
        cestos_para_lavar.update(ciclo_associado=ciclo, status='EM_LAVAGEM')
        
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'errors': form.errors.as_json()}, status=400)

@login_required
@require_POST
@admin_required # <-- PROTEGIDO
def avancar_etapa_ciclo(request, pk):
    ciclo = get_object_or_404(CicloLavagem, pk=pk)
    novo_status = request.POST.get('novo_status')

    if not novo_status in dict(CicloLavagem.STATUS_PROCESSO_CHOICES):
        return JsonResponse({'success': False, 'message': 'Status inválido.'}, status=400)

    ciclo.status_processo = novo_status
    ciclo.data_hora_inicio_etapa = timezone.now()
    
    if novo_status == 'CONCLUIDO':
        ciclo.data_hora_fim = timezone.now()
        ciclo.cestos.all().update(status='CONCLUIDO')
    
    ciclo.save()
    return JsonResponse({'success': True})

@login_required
@require_POST
@admin_required # <-- PROTEGIDO
def adicionar_produto_ciclo(request, pk):
    ciclo = get_object_or_404(CicloLavagem, pk=pk)
    form = ProdutoConsumidoForm(request.POST)
    
    if form.is_valid():
        try:
            produto = form.cleaned_data['produto_estoque']
            quantidade = form.cleaned_data['quantidade_consumida']
            
            if produto.quantidade < quantidade:
                return JsonResponse({'success': False, 'message': f"Estoque insuficiente. Você só tem {produto.quantidade} de {produto}."}, status=400)

            ProdutoConsumidoLavagem.objects.create(
                ciclo=ciclo,
                produto_estoque=produto,
                quantidade_consumida=quantidade
            )
            
            produto.quantidade -= quantidade
            produto.save()
            
            return JsonResponse({'success': True})
        except Exception as e:
             return JsonResponse({'success': False, 'message': str(e)}, status=400)
    
    return JsonResponse({'success': False, 'errors': form.errors.as_json()}, status=400)

@login_required
@require_POST
@admin_required # <-- PROTEGIDO
def remover_produto_ciclo(request, pk):
    try:
        consumo = get_object_or_404(ProdutoConsumidoLavagem, pk=pk)
        produto_estoque = consumo.produto_estoque
        quantidade_devolvida = consumo.quantidade_consumida
        
        produto_estoque.quantidade += quantidade_devolvida
        produto_estoque.save()
        
        consumo.delete()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


# ===================================================================
# === 2. VIEWS DE USUÁRIO COMUM ===
# (Nenhuma, este app é exclusivo para Gestão)
# ===================================================================

# (Vazio, conforme solicitado)