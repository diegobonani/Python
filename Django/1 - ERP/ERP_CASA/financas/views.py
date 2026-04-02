import json
import math
from datetime import date
from dateutil.relativedelta import relativedelta  # Requer: pip install python-dateutil

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.db.models import Sum, Value, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.contrib import messages

# Imports do App Local
from .models import Financa, ContaFinanceira, FinancaCategoria, CenarioFinanceiro
from .forms import FinancaForm, ContaFinanceiraForm, CenarioFinanceiroForm

# Imports de Outros Apps
from core.decorators import admin_required

# ===================================================================
# === 1. GESTÃO FINANCEIRA (ADMIN / SUPER USER) ===
# ===================================================================

@login_required
@admin_required
def gerenciar_financas(request):
    """
    Renderiza a página principal (Dashboard) de Gerenciar Finanças.
    """
    contas_gestao = ContaFinanceira.objects.all().order_by('usuario__username', 'nome')
    form_financa = FinancaForm(usuario=request.user)

    contexto = {
        'contas': contas_gestao,
        'form_lancamento': form_financa,
    }
    return render(request, 'financas/gerenciar_financas.html', contexto)


@login_required
@admin_required
def gerenciar_contas(request):
    """
    Renderiza a página de gerenciamento de Contas Bancárias/Carteiras.
    Restrito a Super Usuários.
    """
    if not request.user.is_superuser:
        messages.error(request, "Acesso negado. Apenas o Super Usuário pode gerenciar contas.")
        return redirect('financas:gerenciar_financas')
        
    contas = ContaFinanceira.objects.all().order_by('usuario__username', 'nome')
    form = ContaFinanceiraForm()
    
    contexto = {
        'contas': contas,
        'form': form,
    }
    return render(request, 'financas/gerenciar_contas.html', contexto)


# ===================================================================
# === 2. CRUD AJAX - LANÇAMENTOS FINANCEIROS ===
# ===================================================================

@login_required
@admin_required
def tabela_financas_partial(request):
    """
    Retorna o HTML da tabela de lançamentos filtrada (usado via AJAX).
    """
    today = timezone.now().date()
    filtro_tipo = request.GET.get('tipo', 'TODOS')
    filtro_conta = request.GET.get('conta_id')

    # Query otimizada com select_related para evitar N+1 queries
    query = Financa.objects.select_related('usuario', 'conta', 'categoria').all()

    if filtro_tipo and filtro_tipo != 'TODOS':
        query = query.filter(tipo=filtro_tipo)
    
    if filtro_conta:
        query = query.filter(conta_id=filtro_conta)

    # Por padrão, filtra pelo mês atual para não carregar tudo de uma vez
    # (Pode remover essa linha se quiser ver o histórico completo sempre)
    query = query.filter(data_registro__year=today.year, data_registro__month=today.month)

    lancamentos = query.order_by('-data_registro')
    
    return render(request, 'partials/_tabela_financas.html', {'lancamentos': lancamentos})


@login_required
@require_POST
@admin_required
def adicionar_financa(request):
    """ Endpoint AJAX para adicionar lançamento. """
    form = FinancaForm(request.POST, usuario=request.user)
    if form.is_valid():
        financa = form.save(commit=False)
        # Se o form não enviou usuário (campo disabled), define como o logado ou ajusta lógica
        if not financa.usuario_id:
            financa.usuario = request.user
        financa.save()
        return JsonResponse({'success': True, 'message': 'Lançamento adicionado!'})
    
    return JsonResponse({'success': False, 'errors': json.loads(form.errors.as_json())}, status=400)


@login_required
@require_POST
@admin_required
def editar_financa(request, pk):
    """ Endpoint AJAX para editar lançamento. """
    financa = get_object_or_404(Financa, pk=pk)
    form = FinancaForm(request.POST, instance=financa, usuario=request.user)
    
    if form.is_valid():
        form.save()
        return JsonResponse({'success': True, 'message': 'Lançamento atualizado!'})
    
    return JsonResponse({'success': False, 'errors': json.loads(form.errors.as_json())}, status=400)


@login_required
@require_POST
@admin_required
def deletar_financa(request, pk):
    """ Endpoint AJAX para excluir lançamento. """
    try:
        financa = get_object_or_404(Financa, pk=pk)
        financa.delete()
        return JsonResponse({'success': True, 'message': 'Lançamento excluído com sucesso.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
@admin_required
def get_financa_json(request, pk):
    """ Retorna dados de um lançamento específico para popular o modal de edição. """
    financa = get_object_or_404(Financa, pk=pk)
    
    data = {
        'id': financa.id,
        'conta_id': financa.conta_id,
        'nome': financa.nome,
        'descricao': financa.descricao,
        'categoria_id': financa.categoria_id,
        'tipo': financa.tipo,
        'conta_tipo': financa.conta_tipo,
        'valor': str(financa.valor), # Decimal para String
        'forma_pagamento_id': financa.forma_pagamento_id,
        'data_registro': financa.data_registro.strftime('%Y-%m-%d'),
        'usuario_id': financa.usuario_id,
    }
    return JsonResponse(data)


# ===================================================================
# === 3. CRUD AJAX - CONTAS FINANCEIRAS ===
# ===================================================================

@login_required
@require_POST
@admin_required
def adicionar_conta(request):
    if not request.user.is_superuser:
         return JsonResponse({'success': False, 'message': 'Permissão negada.'}, status=403)

    form = ContaFinanceiraForm(request.POST)
    if form.is_valid():
        form.save()
        return JsonResponse({'success': True, 'message': 'Conta criada!'})
    return JsonResponse({'success': False, 'errors': json.loads(form.errors.as_json())}, status=400)


@login_required
@require_POST
@admin_required
def editar_conta(request, pk):
    if not request.user.is_superuser:
         return JsonResponse({'success': False, 'message': 'Permissão negada.'}, status=403)

    conta = get_object_or_404(ContaFinanceira, pk=pk)
    form = ContaFinanceiraForm(request.POST, instance=conta)
    if form.is_valid():
        form.save()
        return JsonResponse({'success': True, 'message': 'Conta atualizada!'})
    return JsonResponse({'success': False, 'errors': json.loads(form.errors.as_json())}, status=400)


@login_required
@require_GET
@admin_required
def get_conta_json(request, pk):
    conta = get_object_or_404(ContaFinanceira, pk=pk)
    data = {
        'nome': conta.nome,
        'saldo_inicial': str(conta.saldo_inicial),
        'usuario_id': conta.usuario_id,
        'nao_permite_negativo': conta.nao_permite_negativo,
    }
    return JsonResponse(data)


@login_required
@admin_required
def get_conta_saldo_json(request, pk):
    """ Retorna saldo atualizado de uma conta. """
    conta = get_object_or_404(ContaFinanceira, pk=pk)
    return JsonResponse({
        'saldo_atual': str(conta.saldo_atual), 
        'nao_permite_negativo': conta.nao_permite_negativo
    })


# ===================================================================
# === 4. SIMULAÇÃO FINANCEIRA / SONHOS ===
# ===================================================================

@login_required
def aba_simulacao_financeira_partial(request):
    """
    Lógica da Aba de Simulação (Cenários Financeiros).
    Calcula se o usuário pode pagar pelo sonho com base na sobra mensal.
    """
    user = request.user
    
    # 1. Processar Criação de Novo Cenário
    if request.method == 'POST':
        form = CenarioFinanceiroForm(request.POST)
        if form.is_valid():
            cenario = form.save(commit=False)
            cenario.usuario = user
            cenario.save()
            return redirect('financas:aba_simulacao_financeira_partial')
    else:
        form = CenarioFinanceiroForm()

    # 2. Calcular Fluxo de Caixa Real do Mês Atual
    hoje = date.today()
    lancamentos_mes = Financa.objects.filter(
        data_registro__year=hoje.year, 
        data_registro__month=hoje.month
    )
    
    # Se for superuser vendo tudo, talvez queira filtrar apenas da "Família" ou Usuario principal
    # Aqui filtraremos apenas lançamentos do usuário logado ou todos se for a visão geral administrativa
    if not user.is_superuser:
        lancamentos_mes = lancamentos_mes.filter(usuario=user)

    total_receitas = lancamentos_mes.filter(tipo='Receitas').aggregate(sum=Coalesce(Sum('valor'), Value(0, output_field=DecimalField())))['sum']
    total_despesas = lancamentos_mes.filter(tipo='Despesas').aggregate(sum=Coalesce(Sum('valor'), Value(0, output_field=DecimalField())))['sum']
    
    sobra_real_mensal = float(total_receitas) - float(total_despesas)
    
    # Caso não tenha lançamentos, usa um valor base fictício para teste (ou 0)
    if sobra_real_mensal <= 0:
        sobra_real_mensal = 0.0

    # 3. Processar Cenários
    cenarios = CenarioFinanceiro.objects.filter(usuario=user).order_by('-data_criacao')
    lista_cenarios_processados = []

    for cenario in cenarios:
        valor_objetivo = float(cenario.valor_total) - float(cenario.valor_entrada)
        guardar_por_mes = float(cenario.poupanca_mensal_planejada)
        
        status_cor = 'verde'
        mensagem = 'Plano Viável'
        tempo_estimado_str = "Imediato"

        if guardar_por_mes > sobra_real_mensal:
            status_cor = 'vermelho'
            mensagem = 'Inviável! Valor excede a sobra mensal atual.'
        elif guardar_por_mes <= 0:
            status_cor = 'cinza'
            mensagem = 'Defina valor de poupança.'
        else:
            meses_necessarios = math.ceil(valor_objetivo / guardar_por_mes)
            data_conquista = date.today() + relativedelta(months=+meses_necessarios)
            tempo_estimado_str = f"{meses_necessarios} meses ({data_conquista.strftime('%m/%Y')})"
            
            if meses_necessarios > 60: # 5 anos
                status_cor = 'amarelo'
                mensagem = 'Longo Prazo'

        lista_cenarios_processados.append({
            'objeto': cenario,
            'tempo_estimado': tempo_estimado_str,
            'status_cor': status_cor,
            'mensagem': mensagem
        })

    context = {
        'cenarios_list': lista_cenarios_processados,
        'form_cenario': form,
        'sobra_atual': sobra_real_mensal
    }
    
    return render(request, 'partials/_aba_simulacao_financeira.html', context)


@login_required
def simulacao_financeira_detalhe(request, pk):
    """ Detalhe de um cenário específico (Placeholder). """
    cenario = get_object_or_404(CenarioFinanceiro, pk=pk)
    return render(request, 'financas/detalhe_cenario.html', {'cenario': cenario})


# ===================================================================
# === 5. UTILITÁRIOS E PLACEHOLDERS ===
# ===================================================================

@login_required
def get_categorias_por_tipo(request):
    """ Retorna categorias para preencher selects via AJAX. """
    tipo_custo = request.GET.get('tipo')
    if tipo_custo:
        categorias = FinancaCategoria.objects.filter(tipo_custo=tipo_custo)
    else:
        categorias = FinancaCategoria.objects.all()
    
    data = [{'id': cat.id, 'nome': cat.nome} for cat in categorias.order_by('nome')]
    return JsonResponse(data, safe=False)


@login_required
def get_servicos_veiculo(request):
    """ 
    Placeholder: Retorna lista vazia.
    O gerenciamento operacional de veículos ocorre no app 'carro'.
    Mantido para evitar erro de rota no JS legado.
    """
    return JsonResponse([], safe=False)


@login_required
def get_veiculo_km(request):
    """
    Placeholder: Retorna KM zero.
    O controle de KM ocorre no app 'carro'.
    """
    return JsonResponse({'km_atual': 0})


# ===================================================================
# === 6. ÁREA DO USUÁRIO COMUM ===
# ===================================================================

@login_required
def minhas_financas_view(request):
    """
    Painel Pessoal: Usuário vê apenas seus dados.
    """
    usuario_logado = request.user
    
    if request.method == 'POST':
        form = FinancaForm(request.POST, usuario=usuario_logado)
        if form.is_valid():
            financa = form.save(commit=False)
            financa.usuario = usuario_logado
            financa.save()
            messages.success(request, 'Lançamento salvo com sucesso!')
            return redirect('financas:minhas_financas')
        else:
            messages.error(request, 'Erro ao salvar. Verifique os dados.')
    else:
        form = FinancaForm(usuario=usuario_logado)

    lancamentos = Financa.objects.filter(usuario=usuario_logado).order_by('-data_registro')
    contas = ContaFinanceira.objects.filter(usuario=usuario_logado)
    
    # Cálculos de Totais
    receitas = lancamentos.filter(tipo='Receitas').aggregate(total=Coalesce(Sum('valor'), Value(0, output_field=DecimalField())))['total']
    despesas = lancamentos.filter(tipo='Despesas').aggregate(total=Coalesce(Sum('valor'), Value(0, output_field=DecimalField())))['total']
    saldo_total = receitas - despesas
    saldo_contas = contas.aggregate(total=Coalesce(Sum('saldo_atual'), Value(0, output_field=DecimalField())))['total']

    contexto = {
        'lancamentos': lancamentos,
        'contas_usuario': contas,
        'form': form,
        'saldo_total_usuario': saldo_total,
        'saldo_em_contas': saldo_contas,
        'receitas_usuario': receitas,
        'despesas_usuario': despesas,
    }
    return render(request, 'financas/minhas_financas.html', contexto)