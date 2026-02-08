import json
import datetime
from datetime import timedelta, date
from decimal import Decimal

from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST
from django.db import transaction
from django.db.models import Sum

# Import models e forms
from .models import Alimento, Refeicao, TabelaNutricional, ConsumoEstoque
from .forms import AlimentoForm, RefeicaoForm, TabelaNutricionalForm

# Import de Estoque para integração
from estoque.models import ItemCasa

# =============================================================================
# 1. VIEW PRINCIPAL (LAYOUT E ABAS)
# =============================================================================

@login_required
def gerenciar_alimentacao(request):
    """
    Renderiza a estrutura principal da página (Dashboard).
    """
    form_alimento = AlimentoForm()
    # Passa o usuário para o form para filtrar alimentos e permitir seleção de usuários
    form_refeicao = RefeicaoForm(usuario=request.user)
    
    config_nutri = {
        'mostrar_proteina': True,
        'mostrar_carbo': True,
        'mostrar_gordura': True,
        'mostrar_acucar': True,
        'mostrar_sodio': True,
        'mostrar_fibras': True,
        'mostrar_vd': False 
    }

    context = {
        'titulo': 'Gestão Nutricional',
        'form_alimento': form_alimento,
        'form_refeicao': form_refeicao,
        'config_nutri': config_nutri,
    }
    return render(request, 'alimentacao/gerenciar_alimentacao.html', context)


# =============================================================================
# 2. VIEWS DO DASHBOARD ADMIN (MODAIS)
# =============================================================================

@login_required
def tabela_alimentacao_partial(request):
    """
    Modal 1: Lista Geral de Usuários e Progresso de Hoje.
    """
    try:
        selecao = request.GET.getlist('selecao[]')
        user_ids = [int(sid.replace('user_', '')) for sid in selecao if sid.startswith('user_')]
        
        hoje = date.today()
        
        if not user_ids:
            usuarios = User.objects.filter(is_active=True)
        else:
            usuarios = User.objects.filter(id__in=user_ids)

        dados_usuarios = []
        META_PADRAO = 2500 

        for user in usuarios:
            refeicoes = Refeicao.objects.filter(usuario=user, data=hoje)
            total_cal = sum(r.total_calorias for r in refeicoes) or 0
            
            pct = 0
            if META_PADRAO > 0:
                pct = min(100, int((total_cal / META_PADRAO) * 100))
            
            cor = "success"
            if pct > 100: cor = "danger"
            elif pct > 80: cor = "warning"

            dados_usuarios.append({
                'id': user.id,
                'nome': user.first_name or user.username,
                'calorias': total_cal,
                'meta': META_PADRAO,
                'porcentagem': pct,
                'cor': cor,
                'qtd_refeicoes': refeicoes.count()
            })

        dados_usuarios.sort(key=lambda x: x['calorias'], reverse=True)
        
        return render(request, 'partials/_tabela_alimentacao_dashboard.html', {
            'dados': dados_usuarios
        })

    except Exception as e:
        print(f"--- [ERRO NO PYTHON] {str(e)} ---")
        return HttpResponse(f"Erro no servidor: {str(e)}", status=500)


@login_required
def historico_nutricional_partial(request, user_id):
    """
    Modal 2: Histórico detalhado dos últimos 7 dias de UM usuário.
    """
    usuario = get_object_or_404(User, pk=user_id)
    hoje = date.today()
    historico = []
    
    META_PADRAO = 2500

    for i in range(7):
        dia = hoje - timedelta(days=i)
        refeicoes = Refeicao.objects.filter(usuario=usuario, data=dia)
        total_cal = sum(r.total_calorias for r in refeicoes) or 0
        
        pct = 0
        if META_PADRAO > 0:
            pct = min(100, int((total_cal / META_PADRAO) * 100))
            
        cor = "success"
        if pct > 100: cor = "danger"
        elif pct > 80: cor = "warning"
        elif pct == 0: cor = "secondary"

        historico.append({
            'data': dia,
            'total_cal': total_cal,
            'meta': META_PADRAO,
            'pct': pct,
            'cor': cor,
            'qtd': refeicoes.count()
        })

    return render(request, 'partials/_historico_nutricional_usuario.html', {
        'usuario': usuario,
        'historico': historico
    })


# =============================================================================
# 3. ABA 1: MENU / ALIMENTOS (CRUD)
# =============================================================================

@login_required
def tabela_alimentos_partial(request):
    filtro = request.GET.get('filtro', 'todos')
    alimentos = Alimento.objects.filter(usuario=request.user).order_by('nome')
    
    if filtro == 'SAUDAVEL':
        alimentos = alimentos.filter(classificacao='SAUDAVEL')
    elif filtro == 'LIXO':
        alimentos = alimentos.filter(classificacao='LIXO')
    elif filtro == 'MODERADO':
        alimentos = alimentos.filter(classificacao='MODERADO')

    return render(request, 'partials/_tabela_alimentos.html', {'alimentos': alimentos})

@login_required
@require_POST
def salvar_alimento(request):
    alimento_id = request.POST.get('alimento_id')
    instance_alimento = None
    if alimento_id:
        instance_alimento = get_object_or_404(Alimento, pk=alimento_id, usuario=request.user)
    
    form_alimento = AlimentoForm(request.POST, instance=instance_alimento)
    
    if form_alimento.is_valid():
        alimento = form_alimento.save(commit=False)
        alimento.usuario = request.user
        alimento.save()
        
        if request.POST.get('incluir_nutricao') == 'on':
            try:
                instance_nutri = alimento.nutricao
            except TabelaNutricional.DoesNotExist:
                instance_nutri = None 
            
            form_nutri = TabelaNutricionalForm(request.POST, instance=instance_nutri)
            
            if form_nutri.is_valid():
                nutricao = form_nutri.save(commit=False)
                nutricao.alimento = alimento
                nutricao.save()
            else:
                return JsonResponse({'success': False, 'errors': json.loads(form_nutri.errors.as_json())})
        
        return JsonResponse({'success': True, 'message': 'Alimento salvo com sucesso!'})
    
    return JsonResponse({'success': False, 'errors': json.loads(form_alimento.errors.as_json())})

@login_required
def get_alimento_json(request, pk):
    obj = get_object_or_404(Alimento, pk=pk, usuario=request.user)
    data = {
        'id': obj.id, 'nome': obj.nome, 'classificacao': obj.classificacao,
        'calorias': obj.calorias, 'tem_nutricao': False 
    }
    if hasattr(obj, 'nutricao'):
        n = obj.nutricao
        data.update({
            'tem_nutricao': True, 'proteinas': n.proteinas, 'carboidratos': n.carboidratos,
            'gorduras_totais': n.gorduras_totais, 'acucares': n.acucares,
            'sodio': n.sodio, 'fibras': n.fibras
        })
    return JsonResponse(data)

@login_required
@require_POST
def excluir_alimento(request, pk):
    obj = get_object_or_404(Alimento, pk=pk, usuario=request.user)
    obj.delete() 
    return JsonResponse({'success': True, 'message': 'Alimento removido.'})


# =============================================================================
# 4. ABA 2: DIÁRIO / HISTÓRICO (COM SUPORTE A MÚLTIPLOS USUÁRIOS)
# =============================================================================

@login_required
def tabela_historico_partial(request):
    data_str = request.GET.get('semana', None)
    if data_str:
        try:
            data_ref = datetime.datetime.strptime(data_str, '%Y-%m-%d').date()
        except ValueError:
            data_ref = date.today()
    else:
        data_ref = date.today()

    filtro_tipo = request.GET.get('tipo_refeicao', '')
    inicio_semana = data_ref - timedelta(days=data_ref.weekday())
    fim_semana = inicio_semana + timedelta(days=6)

    refeicoes_banco = Refeicao.objects.filter(
        usuario=request.user,
        data__range=[inicio_semana, fim_semana]
    ).prefetch_related('alimentos', 'usuario')

    if filtro_tipo and filtro_tipo != 'TODOS':
        refeicoes_banco = refeicoes_banco.filter(tipo=filtro_tipo)

    refeicoes_banco = refeicoes_banco.order_by('data', 'id')
    dias_semana = []
    nomes_dias = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
    
    for i in range(7):
        data_atual = inicio_semana + timedelta(days=i)
        refeicoes_do_dia = [r for r in refeicoes_banco if r.data == data_atual]
        dias_semana.append({
            'nome': nomes_dias[i], 'data': data_atual,
            'is_hoje': data_atual == date.today(), 'refeicoes': refeicoes_do_dia
        })

    context = {
        'dias_semana': dias_semana, 'inicio_semana': inicio_semana,
        'fim_semana': fim_semana, 'filtro_atual': filtro_tipo,
        'semana_anterior': (inicio_semana - timedelta(days=7)).strftime('%Y-%m-%d'),
        'proxima_semana': (inicio_semana + timedelta(days=7)).strftime('%Y-%m-%d')
    }
    return render(request, 'partials/_tabela_historico.html', context)

@login_required
def get_refeicao_json(request, pk):
    """
    Retorna dados da refeição e o ID do dono para pré-seleção.
    """
    refeicao = get_object_or_404(Refeicao, pk=pk)
    alimentos_ids = list(refeicao.alimentos.values_list('id', flat=True))
    
    data = {
        'id': refeicao.id, 
        'data': refeicao.data.strftime('%Y-%m-%d'),
        'tipo': refeicao.tipo, 
        'alimentos': alimentos_ids,
        'descricao_adicional': refeicao.descricao_adicional or '',
        'observacoes': refeicao.observacoes or '',
        'usuario_id': refeicao.usuario.id  # Enviamos o ID do dono atual
    }
    return JsonResponse(data)

@login_required
@require_POST
def salvar_refeicao(request):
    """
    Salva ou Edita Refeição. Suporta criação em massa (para vários usuários).
    """
    refeicao_id = request.POST.get('refeicao_id')
    
    # Se tem ID, buscamos a instância (Edit Mode)
    if refeicao_id:
        instance = get_object_or_404(Refeicao, pk=refeicao_id)
        form = RefeicaoForm(request.POST, instance=instance, usuario=request.user)
    else:
        form = RefeicaoForm(request.POST, usuario=request.user)
        
    itens_estoque_json = request.POST.get('itens_estoque_json') 

    if form.is_valid():
        try:
            with transaction.atomic():
                # 1. Identifica para quais usuários atribuir a refeição
                usuarios_selecionados = form.cleaned_data.get('para_quem')
                
                # Se não selecionou ninguém, assume o usuário logado
                if not usuarios_selecionados:
                    lista_usuarios = [request.user]
                else:
                    lista_usuarios = list(usuarios_selecionados)

                # --- MODO EDIÇÃO (Alterar existente) ---
                if refeicao_id:
                    refeicao = form.save(commit=False)
                    # Se selecionou um usuário na edição, transferimos a refeição para o primeiro selecionado
                    if usuarios_selecionados:
                        refeicao.usuario = usuarios_selecionados[0]
                    
                    refeicao.save()
                    form.save_m2m()
                    
                    # Processa estoque (adiciona novos consumos se houver)
                    processar_estoque(refeicao, itens_estoque_json)
                    
                    return JsonResponse({'success': True, 'message': 'Refeição atualizada!'})

                # --- MODO CRIAÇÃO (Pode ser em massa) ---
                else:
                    primeira_refeicao = None
                    
                    for user_target in lista_usuarios:
                        # Cria uma refeição separada para cada usuário selecionado
                        nova_refeicao = Refeicao(
                            usuario=user_target,
                            data=form.cleaned_data['data'],
                            tipo=form.cleaned_data['tipo'],
                            descricao_adicional=form.cleaned_data['descricao_adicional'],
                            observacoes=form.cleaned_data['observacoes']
                        )
                        nova_refeicao.save()
                        
                        # Copia os alimentos ManyToMany
                        nova_refeicao.alimentos.set(form.cleaned_data['alimentos'])
                        
                        # Processa estoque individualmente para cada cópia
                        processar_estoque(nova_refeicao, itens_estoque_json)
                        
                        if not primeira_refeicao:
                            primeira_refeicao = nova_refeicao

                    msg = 'Refeição registrada!'
                    if len(lista_usuarios) > 1:
                        msg = f'Refeição registrada para {len(lista_usuarios)} usuários!'

            return JsonResponse({'success': True, 'message': msg})
            
        except Exception as e:
            return JsonResponse({'success': False, 'errors': {'geral': [f'Erro: {str(e)}']}})
            
    return JsonResponse({'success': False, 'errors': json.loads(form.errors.as_json())})

def processar_estoque(refeicao, json_dados):
    """
    Função auxiliar para processar baixa de estoque e vincular à refeição.
    """
    if not json_dados:
        return

    lista_estoque = json.loads(json_dados)
    descricao_itens = []
    
    for item_dict in lista_estoque:
        item_id = item_dict.get('id')
        qtd = Decimal(str(item_dict.get('quantidade')))
        
        # Bloqueia o item para evitar condição de corrida
        item_db = ItemCasa.objects.select_for_update().get(id=item_id)
        
        if item_db.quantidade >= qtd:
            item_db.quantidade -= qtd
            item_db.save()
            
            ConsumoEstoque.objects.create(
                refeicao=refeicao, 
                item_estoque=item_db, 
                quantidade=qtd
            )
            unidade = item_db.unidade.sigla if item_db.unidade else 'UN'
            descricao_itens.append(f"{item_db.nome} ({qtd} {unidade})")
        else:
            raise ValueError(f"Saldo insuficiente para {item_db.nome}. Disp: {item_db.quantidade}")

    # Atualiza a descrição da refeição com o que foi consumido
    if descricao_itens:
        texto = " | Estoque: " + ", ".join(descricao_itens)
        if refeicao.descricao_adicional:
            refeicao.descricao_adicional += texto
        else:
            refeicao.descricao_adicional = texto
        refeicao.save()


@login_required
@require_POST
def excluir_refeicao(request, pk):
    try:
        with transaction.atomic():
            refeicao = get_object_or_404(Refeicao, pk=pk, usuario=request.user)
            consumos = ConsumoEstoque.objects.filter(refeicao=refeicao)
            itens_estornados = []
            
            for consumo in consumos:
                item_db = consumo.item_estoque
                item_db.quantidade += consumo.quantidade
                item_db.save()
                itens_estornados.append(item_db.nome)
            
            refeicao.delete()
            msg = 'Excluído.' + (f' Devolvidos: {", ".join(itens_estornados)}' if itens_estornados else '')
            return JsonResponse({'success': True, 'message': msg})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


# =============================================================================
# 5. APIS (GRÁFICOS E VERIFICAÇÕES)
# =============================================================================

@login_required
def api_resumo_nutricional(request):
    hoje = date.today()
    refeicoes = Refeicao.objects.filter(usuario=request.user, data=hoje)
    
    total_calorias = 0
    total_proteinas = 0
    total_carbos = 0
    total_gorduras = 0
    
    for r in refeicoes:
        total_calorias += r.total_calorias
        macros = r.total_macros 
        total_proteinas += macros['prot']
        total_carbos += macros['carb']
        total_gorduras += macros['gord']

    META_CAL = 2500
    META_PROT = 160
    META_CARB = 250
    META_GORD = 70

    data = {
        'calorias': {
            'consumido': int(total_calorias),
            'meta': META_CAL,
            'restante': max(0, META_CAL - int(total_calorias)),
            'pct': min(100, int((total_calorias / META_CAL) * 100))
        },
        'macros': {
            'proteina': round(float(total_proteinas), 1),
            'carbo': round(float(total_carbos), 1),
            'gordura': round(float(total_gorduras), 1),
            'meta_p': META_PROT,
            'meta_c': META_CARB,
            'meta_g': META_GORD
        }
    }
    return JsonResponse(data)

@login_required
def api_check_duplicidade(request):
    """
    Verifica se já existe uma refeição do mesmo tipo na data informada para o usuário logado.
    """
    data_str = request.GET.get('data')
    tipo = request.GET.get('tipo')
    refeicao_id = request.GET.get('id') # ID atual se for edição

    if not data_str or not tipo:
        return JsonResponse({'exists': False})

    # Query base
    qs = Refeicao.objects.filter(usuario=request.user, data=data_str, tipo=tipo)

    # Se for edição, exclui o próprio ID da verificação
    if refeicao_id:
        qs = qs.exclude(id=refeicao_id)

    exists = qs.exists()
    
    return JsonResponse({'exists': exists})