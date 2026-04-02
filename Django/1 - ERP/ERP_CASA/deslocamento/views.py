from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import DiaDeDeslocamento, Percurso, LocalizacaoFrequente
from .forms import DiaDeDeslocamentoForm
from carro.models import Veiculo
import requests
import json
from decimal import Decimal
import datetime
import time

# Função de permissão
def is_admin_or_superuser(user):
    return user.is_superuser or (hasattr(user, 'perfil') and user.perfil.tipo == 'Administrador')

@login_required
def localizacoes_json(request):
    localizacoes = LocalizacaoFrequente.objects.filter(usuario=request.user).order_by('nome')
    data = [{'id': l.id, 'nome': l.nome, 'endereco': l.endereco_texto} for l in localizacoes]
    return JsonResponse({'localizacoes': data}, safe=False)

# ===================================================================
# 1. FUNÇÕES AUXILIARES
# ===================================================================

def _geocodificar_tomtom(endereco):
    API_KEY = getattr(settings, 'TOM_TOM_API_KEY', None)
    if not API_KEY: return None
    encoded_addr = requests.utils.quote(endereco)
    url = f"https://api.tomtom.com/search/2/search/{encoded_addr}.json"
    params = {'key': API_KEY, 'limit': 1, 'countrySet': 'BR', 'language': 'pt-BR'}
    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('results'):
                pos = data['results'][0]['position']
                return [float(pos['lon']), float(pos['lat'])]
    except Exception as e: print(f"Erro TomTom Geo: {e}")
    return None

def _calcular_percurso_tomtom(waypoints_json):
    API_KEY = getattr(settings, 'TOM_TOM_API_KEY', None)
    if not API_KEY: return {'error': 'Chave TomTom ausente.'}

    try: waypoints_list = json.loads(waypoints_json)
    except: return {'error': 'Dados inválidos.'}
    if len(waypoints_list) < 2: return {'error': 'Defina Origem e Destino.'}

    coords_para_url = []; enderecos_finais = []
    for wp in waypoints_list:
        lat, lon = None, None
        if 'lon' in wp and 'lat' in wp:
            lat, lon = float(wp['lat']), float(wp['lon'])
            enderecos_finais.append(wp.get('address', 'Mapa'))
        else:
            address = wp.get('address', '').strip()
            if not address: continue
            c = _geocodificar_tomtom(address)
            if not c: return {'error': f"Endereço não achado: {address}"}
            lon, lat = c[0], c[1]
            enderecos_finais.append(address)
        coords_para_url.append(f"{lat},{lon}")

    if len(coords_para_url) < 2: return {'error': 'Falha coord.'}

    locations_str = ":".join(coords_para_url)
    url = f"https://api.tomtom.com/routing/1/calculateRoute/{locations_str}/json"
    params = {'key': API_KEY, 'traffic': 'true', 'travelMode': 'car', 'routeType': 'fastest', 'language': 'pt-BR'}

    try:
        r = requests.get(url, params=params, timeout=15)
        if r.status_code != 200: return {'error': f'TomTom API: {r.text}'}
        data = r.json()
    except Exception as e: return {'error': f'Conexão: {e}'}

    if not data.get('routes'): return {'error': 'Rota não encontrada.'}

    legs = data['routes'][0]['legs']
    segmentos = []
    for i, leg in enumerate(legs):
        origem = enderecos_finais[i]
        destino = enderecos_finais[i+1]
        summary = leg['summary']
        dist_km = Decimal(summary['lengthInMeters'] / 1000).quantize(Decimal('0.01'))
        temp_min = int(summary['travelTimeInSeconds'] // 60)
        segmentos.append({'origem': origem, 'destino': destino, 'km_trecho': dist_km, 'tempo_trecho_min': temp_min})

    return {'segmentos': segmentos}

def _obter_consumo_veiculo(veiculo, tipo_combustivel, tipo_trajeto):
    """
    Retorna o consumo correto do cadastro do veículo.
    """
    if not veiculo: return Decimal('10.0')

    # --- CORREÇÃO CRÍTICA: REFRESH DO BANCO ---
    # Isso garante que se você alterou o Sandero no Admin, pegaremos o valor novo (13.5)
    # e não o valor que estava na memória quando o servidor subiu.
    veiculo.refresh_from_db()

    # Pega valores seguros do banco
    c_gas_cid = veiculo.consumo_cidade_gasolina if veiculo.consumo_cidade_gasolina is not None else Decimal('13.5')
    c_gas_est = veiculo.consumo_estrada_gasolina if veiculo.consumo_estrada_gasolina is not None else Decimal('15.5')
    c_eta_cid = veiculo.consumo_cidade_etanol if veiculo.consumo_cidade_etanol is not None else Decimal('10.5')
    c_eta_est = veiculo.consumo_estrada_etanol if veiculo.consumo_estrada_etanol is not None else Decimal('12.0')

    resultado = Decimal('10.0')

    if tipo_combustivel == 'GASOLINA':
        if tipo_trajeto == 'CIDADE': resultado = c_gas_cid
        elif tipo_trajeto == 'ESTRADA': resultado = c_gas_est
        else: resultado = (c_gas_cid + c_gas_est) / 2
    else: # ETANOL
        if tipo_trajeto == 'CIDADE': resultado = c_eta_cid
        elif tipo_trajeto == 'ESTRADA': resultado = c_eta_est
        else: resultado = (c_eta_cid + c_eta_est) / 2
        
    return resultado

def _calcular_custo_flex(km_total, consumo_final, preco_litro):
    # Converte tudo para Decimal para precisão financeira
    km = Decimal(str(km_total))
    con = Decimal(str(consumo_final))
    prc = Decimal(str(preco_litro))
    
    if km > 0 and con > 0 and prc > 0:
        litros = km / con
        custo = litros * prc
        return custo.quantize(Decimal('0.01'))
    return Decimal('0.00')

# ===================================================================
# 2. VIEWS
# ===================================================================

@login_required
@user_passes_test(is_admin_or_superuser)
def gerenciar_deslocamentos(request):
    form = DiaDeDeslocamentoForm(usuario=request.user)
    deslocamentos = DiaDeDeslocamento.objects.all().order_by('-data', '-id')
    contexto = {
        'form_adicionar': form,
        'dias_deslocamento': deslocamentos,
        'localizacoes_frequentes': LocalizacaoFrequente.objects.filter(usuario=request.user),
        'tomtom_api_key': getattr(settings, 'TOM_TOM_API_KEY', '')
    }
    return render(request, 'deslocamento/gerenciar_deslocamento.html', contexto)

@login_required
@require_POST
@user_passes_test(is_admin_or_superuser)
def registrar_dia_deslocamento(request):
    form = DiaDeDeslocamentoForm(request.POST, usuario=request.user)
    force_save = request.POST.get('force_save') == 'true'
    
    if form.is_valid():
        if not force_save and DiaDeDeslocamento.objects.filter(usuario=request.user, data=form.cleaned_data.get('data')).exists():
            return JsonResponse({'confirm_needed': True, 'message': 'Já existe rota hoje. Adicionar?'})

        wps_json = form.cleaned_data.pop('enderecos_waypoints')
        veiculo = form.cleaned_data.get('veiculo')
        tipo_comb = form.cleaned_data.get('tipo_combustivel')
        tipo_traj = form.cleaned_data.get('tipo_trajeto')
        valor_litro = form.cleaned_data.get('valor_litro')
        c_manual = form.cleaned_data.get('consumo_manual')
        
        consumo = Decimal('10.0')
        if c_manual: consumo = c_manual
        elif veiculo: consumo = _obter_consumo_veiculo(veiculo, tipo_comb, tipo_traj)
        
        calculo = _calcular_percurso_tomtom(wps_json)
        if 'error' in calculo: return JsonResponse({'success': False, 'message': calculo['error']}, status=400)
        
        segs = calculo['segmentos']
        km = sum(s['km_trecho'] for s in segs)
        tempo = sum(s['tempo_trecho_min'] for s in segs)
        custo = _calcular_custo_flex(km, consumo, valor_litro)
        
        dia = form.save(commit=False)
        dia.usuario = request.user; dia.km_total_apurado = km; dia.tempo_total_min = tempo; dia.custo_total_estimado = custo
        if hasattr(dia, 'tipo_trajeto'): dia.tipo_trajeto = tipo_traj
        dia.save()
        
        for i, s in enumerate(segs):
            Percurso.objects.create(dia_de_deslocamento=dia, sequencia=i+1, origem=s['origem'], destino=s['destino'], km_trecho=s['km_trecho'], tempo_trecho_min=s['tempo_trecho_min'])
        
        return JsonResponse({'success': True, 'message': f'Salvo! KM: {km} | Custo: R$ {custo}'})
    
    return JsonResponse({'success': False, 'errors': json.loads(form.errors.as_json())}, status=400)

@login_required
def resumo_deslocamento_partial(request):
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    qs = DiaDeDeslocamento.objects.all().order_by('-data', '-id')
    if data_inicio: qs = qs.filter(data__gte=data_inicio)
    if data_fim: qs = qs.filter(data__lte=data_fim)
    return render(request, 'partials/_tabela_deslocamentos.html', {'dias_deslocamento': qs})

@login_required
def detalhes_percurso_ajax(request, pk):
    dia = get_object_or_404(DiaDeDeslocamento, pk=pk)
    qs_percursos = dia.percursos.all().order_by('sequencia')
    
    # 1. Determina consumo
    consumo_medio = Decimal('10.0')
    if dia.consumo_manual:
        consumo_medio = dia.consumo_manual
    elif dia.veiculo:
        consumo_medio = _obter_consumo_veiculo(dia.veiculo, dia.tipo_combustivel, dia.tipo_trajeto)
    
    # 2. Calcula dados por trecho e soma totais
    percursos_view = []
    preco_litro = dia.valor_litro if dia.valor_litro else Decimal('0.00')
    
    total_litros = Decimal('0.00') # Variável acumuladora

    for p in qs_percursos:
        if consumo_medio > 0:
            litros = p.km_trecho / consumo_medio
            p.litros_estimados = litros
            p.custo_estimado = litros * preco_litro
            
            # Soma ao total
            total_litros += Decimal(str(litros)) 
        else:
            p.litros_estimados = 0
            p.custo_estimado = 0
        
        percursos_view.append(p)

    # 3. JSON Mapa
    wps = []
    if qs_percursos.exists():
        wps.append({'address': qs_percursos.first().origem, 'type': 'start'})
        for p in qs_percursos:
            tipo = 'end' if p == qs_percursos.last() else 'waypoint'
            wps.append({'address': p.destino, 'type': tipo})

    contexto = {
        'dia_deslocamento': dia, 
        'percursos': percursos_view, 
        'waypoints_json': json.dumps(wps),
        'consumo_aplicado': consumo_medio,
        'total_litros': total_litros # <--- Passando o total para o template
    }
    return render(request, 'partials/_lista_percursos_detalhe.html', contexto)

@login_required
@require_POST
def deletar_deslocamento_ajax(request, pk):
    get_object_or_404(DiaDeDeslocamento, pk=pk).delete()
    return JsonResponse({'success': True})

@login_required
def get_deslocamento_json(request, pk):
    d = get_object_or_404(DiaDeDeslocamento, pk=pk)
    wps = []
    percursos = d.percursos.all().order_by('sequencia')
    if percursos.exists():
        wps.append({'address': percursos[0].origem})
        for p in percursos: wps.append({'address': p.destino})
            
    return JsonResponse({
        'veiculo_id': d.veiculo_id,
        'data': d.data.strftime('%Y-%m-%d'),
        'observacoes': d.observacoes,
        'tipo_combustivel': getattr(d, 'tipo_combustivel', 'GASOLINA'),
        'tipo_trajeto': getattr(d, 'tipo_trajeto', 'CIDADE'),
        'valor_litro': str(getattr(d, 'valor_litro', '0.00')),
        'consumo_manual': str(getattr(d, 'consumo_manual', '') or ''),
        'waypoints': wps
    })

@login_required
@require_POST
def editar_deslocamento_ajax(request, pk):
    dia = get_object_or_404(DiaDeDeslocamento, pk=pk)
    form = DiaDeDeslocamentoForm(request.POST, instance=dia, usuario=request.user)
    wps_json = request.POST.get('enderecos_waypoints')
    
    if not wps_json or wps_json == '[]': form.fields['enderecos_waypoints'].required = False
    if 'consumo_medio' in form.fields: form.fields['consumo_medio'].required = False

    if form.is_valid():
        obj = form.save(commit=False)
        
        # Decide Consumo
        consumo = Decimal('10.0')
        if obj.consumo_manual:
            consumo = obj.consumo_manual
        elif obj.veiculo:
            # Refresh crucial para pegar dados atualizados do carro
            obj.veiculo.refresh_from_db()
            consumo = _obter_consumo_veiculo(obj.veiculo, obj.tipo_combustivel, obj.tipo_trajeto)

        print(f"DEBUG: Consumo usado para o cálculo: {consumo}") # <--- OLHE ISSO NO TERMINAL

        if wps_json and wps_json != '[]':
            # ROTA MUDOU: Recalcula KM e Custo
            calc = _calcular_percurso_tomtom(wps_json)
            if 'error' in calc: return JsonResponse({'success': False, 'errors': {'rota': [calc['error']]}}, status=400)
            
            segs = calc['segmentos']
            obj.km_total_apurado = sum(s['km_trecho'] for s in segs)
            obj.tempo_total_min = sum(s['tempo_trecho_min'] for s in segs)
            
            obj.custo_total_estimado = _calcular_custo_flex(obj.km_total_apurado, consumo, obj.valor_litro)
            obj.save()
            
            dia.percursos.all().delete()
            for i, s in enumerate(segs):
                Percurso.objects.create(dia_de_deslocamento=dia, sequencia=i+1, origem=s['origem'], destino=s['destino'], km_trecho=s['km_trecho'], tempo_trecho_min=s['tempo_trecho_min'])
        else:
            # ROTA IGUAL: Recalcula SÓ o Custo (Baseado na KM antiga e NOVO CONSUMO)
            print("Recalculando custo com nova configuração...")
            # Garante que KM existe
            km = obj.km_total_apurado if obj.km_total_apurado else Decimal('0.00')
            
            obj.custo_total_estimado = _calcular_custo_flex(km, consumo, obj.valor_litro)
            obj.save()

        return JsonResponse({'success': True, 'message': f'Atualizado! Novo Custo: R$ {obj.custo_total_estimado}'})
        
    return JsonResponse({'success': False, 'errors': json.loads(form.errors.as_json())}, status=400)