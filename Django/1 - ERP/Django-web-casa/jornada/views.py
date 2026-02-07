# Em: jornada/views.py

from django.template.loader import render_to_string
from weasyprint import HTML
import datetime
import json
import csv 
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.views.decorators.http import require_POST
from django.db.models import Sum, Q, Value, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import IntegrityError # Importa o erro de integridade

# Imports deste app
from .models import RegistroPonto, RegistroBalanço, Materia, Nota, TipoDiaJornada
from .forms import (
    RegistroPontoForm, RegistroPontoAdminForm, 
    RegistroBalançoForm, RegistroBalançoAdminForm, # <-- NOVOS FORMS
    MateriaForm, NotaForm
)

# Imports de outros apps
from core.decorators import admin_required 

# ===================================================================
# === 1. VIEWS DE GESTÃO (ADMINISTRADORES / SUPER USERS) ===
# ===================================================================

@login_required
@admin_required
def gerenciar_jornada_view(request):
    """
    Página de Gestão de Jornada, AGORA COM ABAS (Jornada e Balanço).
    """
    usuarios_trabalhando = User.objects.filter(perfil__esta_trabalhando=True).order_by('username')
    
    # --- Lógica de Abas ---
    aba_ativa = request.GET.get('aba', 'jornada') # 'jornada' ou 'balanco'

    # --- Lógica de Filtros (comum a ambas as abas) ---
    filtro_tipo = request.GET.get('filtro_tipo', 'dia')
    usuario_id_filtro = request.GET.get('usuario_id')

    hoje_str = datetime.date.today().strftime('%Y-%m-%d')
    mes_str = datetime.date.today().strftime('%Y-%m')
    data_filtro_str = request.GET.get('data', hoje_str)
    mes_filtro_str = request.GET.get('mes', mes_str)
    data_inicio_str = request.GET.get('data_inicio', hoje_str)
    data_fim_str = request.GET.get('data_fim', hoje_str)

    # --- Lógica de Usuário Obrigatório ---
    usuario_selecionado = None
    if usuario_id_filtro and usuario_id_filtro.isdigit():
        usuario_selecionado = usuarios_trabalhando.filter(pk=int(usuario_id_filtro)).first()
    
    if not usuario_selecionado and usuarios_trabalhando.exists():
        usuario_selecionado = usuarios_trabalhando.first()

    # --- Inicializa variáveis de contexto ---
    registros_jornada = RegistroPonto.objects.none()
    registros_balanco = RegistroBalanço.objects.none()
    soma_horas_almoco = Decimal('0.0')
    soma_horas_trabalhadas = Decimal('0.0')
    soma_horas_extras = Decimal('0.0')
    soma_valor_receber = Decimal('0.0')
    soma_horas_balanco = Decimal('0.0')
    soma_valor_balanco = Decimal('0.0')
    
    # --- Lógica de Filtro de Data ---
    if usuario_selecionado:
        # Define a query base dependendo da aba
        if aba_ativa == 'jornada':
            query_base = RegistroPonto.objects.filter(usuario=usuario_selecionado)
            registros_model = RegistroPonto
        else: # aba_ativa == 'balanco'
            query_base = RegistroBalanço.objects.filter(usuario=usuario_selecionado)
            registros_model = RegistroBalanço

        # Aplica o filtro de data selecionado
        if filtro_tipo == 'dia':
            try:
                data_filtro = datetime.datetime.strptime(data_filtro_str, '%Y-%m-%d').date()
                registros = query_base.filter(data=data_filtro)
            except ValueError:
                data_filtro_str = hoje_str
                registros = query_base.filter(data=datetime.date.today())
        
        elif filtro_tipo == 'mes':
            try:
                if not mes_filtro_str: mes_filtro_str = mes_str
                mes_ano = datetime.datetime.strptime(mes_filtro_str, '%Y-%m').date()
                registros = query_base.filter(data__year=mes_ano.year, data__month=mes_ano.month)
            except ValueError:
                mes_filtro_str = mes_str
                registros = query_base.none() # Evita erro se o mês for inválido
        
        elif filtro_tipo == 'periodo':
            try:
                data_inicio = datetime.datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
                data_fim = datetime.datetime.strptime(data_fim_str, '%Y-%m-%d').date()
                registros = query_base.filter(data__range=[data_inicio, data_fim])
            except ValueError:
                registros = query_base.none() # Evita erro se datas inválidas
        
        # --- Cálculo dos Totais (depende da aba) ---
        if aba_ativa == 'jornada':
            registros_jornada = registros.select_related('usuario__perfil').order_by('data', 'entrada')
            for r in registros_jornada:
                soma_horas_almoco += r.horas_almoco
                soma_horas_trabalhadas += r.horas_trabalhadas
                soma_horas_extras += r.horas_extras
                soma_valor_receber += r.valor_receber
        else: # aba_ativa == 'balanco'
            registros_balanco = registros.select_related('usuario__perfil').order_by('data', 'entrada')
            for r in registros_balanco:
                soma_horas_balanco += r.horas_trabalhadas
                soma_valor_balanco += r.valor_receber

    contexto = {
        'aba_ativa': aba_ativa,
        'registros_jornada': registros_jornada,
        'registros_balanco': registros_balanco,
        'usuarios_trabalhando': usuarios_trabalhando,
        
        'filtro_tipo': filtro_tipo,
        'data_filtro': data_filtro_str,
        'mes_filtro': mes_filtro_str,
        'data_inicio': data_inicio_str,
        'data_fim': data_fim_str,
        
        'usuario_selecionado': usuario_selecionado,
        'usuario_selecionado_id': usuario_selecionado.id if usuario_selecionado else None,
        
        # Formulários para os Modais
        'form_admin_jornada': RegistroPontoAdminForm(),
        'form_admin_balanco': RegistroBalançoAdminForm(),

        # Totais da Aba JORNADA
        'soma_horas_almoco': soma_horas_almoco,
        'soma_horas_trabalhadas': soma_horas_trabalhadas,
        'soma_horas_extras': soma_horas_extras,
        'soma_valor_receber': soma_valor_receber,
        
        # Totais da Aba BALANÇO
        'soma_horas_balanco': soma_horas_balanco,
        'soma_valor_balanco': soma_valor_balanco,
    }
    return render(request, 'jornada/gerenciar_jornada.html', contexto)


@login_required
@admin_required
def gerenciar_estudos_view(request):
    """ Página de Gestão de Estudos. """
    usuarios_estudando = User.objects.filter(perfil__esta_estudando=True).order_by('username')
    usuario_id_filtro = request.GET.get('usuario_id')
    materias = Materia.objects.all()

    if usuario_id_filtro:
        materias = materias.filter(usuario_id=usuario_id_filtro)
    else:
        materias = materias.filter(usuario__in=usuarios_estudando)

    materias = materias.select_related('usuario').prefetch_related('notas').order_by('usuario__username', 'nome')

    contexto = {
        'materias_todas': materias,
        'usuarios_estudando': usuarios_estudando,
        'usuario_id_filtro': int(usuario_id_filtro) if usuario_id_filtro else None,
    }
    return render(request, 'jornada/gerenciar_estudos.html', contexto)

# --- AÇÕES AJAX DE GESTÃO (JORNADA) ---

@login_required
@require_POST
@admin_required
def admin_registrar_ponto_ajax(request):
    """ Gestor cria registro de JORNADA. """
    form = RegistroPontoAdminForm(request.POST)
    if form.is_valid():
        try:
            form.save()
            return JsonResponse({'success': True, 'message': 'Registro de Jornada criado!'})
        except IntegrityError: # Captura o erro de unique_together
            return JsonResponse({'success': False, 'message': 'Já existe um registro deste tipo (Ex: Normal) para este colaborador nesta data.'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Erro inesperado: {e}'}, status=400)
            
    return JsonResponse({'success': False, 'errors': json.loads(form.errors.as_json())}, status=400)

@login_required
@admin_required
def admin_get_ponto_json(request, pk):
    """ Gestor busca dados de um registro de JORNADA. """
    ponto = get_object_or_404(RegistroPonto, pk=pk)
    data = {
        'data': ponto.data.strftime('%Y-%m-%d'),
        'tipo_dia': ponto.tipo_dia, 
        'entrada': ponto.entrada.strftime('%H:%M') if ponto.entrada else '',
        'saida_almoco': ponto.saida_almoco.strftime('%H:%M') if ponto.saida_almoco else '',
        'retorno_almoco': ponto.retorno_almoco.strftime('%H:%M') if ponto.retorno_almoco else '',
        'saida': ponto.saida.strftime('%H:%M') if ponto.saida else '',
        'atestado_cid': ponto.atestado_cid,
        'atestado_crm': ponto.atestado_crm,
        'atestado_obs': ponto.atestado_obs,
        'usuario_nome': ponto.usuario.username 
    }
    return JsonResponse(data)

@login_required
@require_POST
@admin_required
def admin_editar_ponto_ajax(request, pk):
    """ Gestor edita um registro de JORNADA. """
    ponto = get_object_or_404(RegistroPonto, pk=pk)
    form = RegistroPontoForm(request.POST, instance=ponto)
    if form.is_valid():
        form.save()
        return JsonResponse({'success': True, 'message': 'Registro de Jornada atualizado!'})
    return JsonResponse({'success': False, 'errors': json.loads(form.errors.as_json())}, status=400)

@login_required
@require_POST
@admin_required
def admin_deletar_ponto_ajax(request, pk):
    """ Gestor deleta um registro de JORNADA. """
    ponto = get_object_or_404(RegistroPonto, pk=pk)
    ponto.delete()
    return JsonResponse({'success': True, 'message': 'Registro de Jornada deletado!'})

# --- NOVAS AÇÕES AJAX DE GESTÃO (BALANÇO) ---

@login_required
@require_POST
@admin_required
def admin_registrar_balanco_ajax(request):
    """ Gestor cria registro de BALANÇO. """
    # Nota: request.FILES é necessário para o Anexo
    form = RegistroBalançoAdminForm(request.POST, request.FILES) 
    if form.is_valid():
        form.save()
        return JsonResponse({'success': True, 'message': 'Registro de Balanço criado!'})
    return JsonResponse({'success': False, 'errors': json.loads(form.errors.as_json())}, status=400)

@login_required
@admin_required
def admin_get_balanco_json(request, pk):
    """ Gestor busca dados de um registro de BALANÇO. """
    balanco = get_object_or_404(RegistroBalanço, pk=pk)
    data = {
        'data': balanco.data.strftime('%Y-%m-%d'),
        'loja': balanco.loja,
        'entrada': balanco.entrada.strftime('%H:%M') if balanco.entrada else '',
        'saida': balanco.saida.strftime('%H:%M') if balanco.saida else '',
        'anexo_url': balanco.anexo.url if balanco.anexo else None,
        'usuario_nome': balanco.usuario.username 
    }
    return JsonResponse(data)

@login_required
@require_POST
@admin_required
def admin_editar_balanco_ajax(request, pk):
    """ Gestor edita um registro de BALANÇO. """
    balanco = get_object_or_404(RegistroBalanço, pk=pk)
    form = RegistroBalançoForm(request.POST, request.FILES, instance=balanco)
    if form.is_valid():
        form.save()
        return JsonResponse({'success': True, 'message': 'Registro de Balanço atualizado!'})
    return JsonResponse({'success': False, 'errors': json.loads(form.errors.as_json())}, status=400)

@login_required
@require_POST
@admin_required
def admin_deletar_balanco_ajax(request, pk):
    """ Gestor deleta um registro de BALANÇO. """
    balanco = get_object_or_404(RegistroBalanço, pk=pk)
    balanco.delete()
    return JsonResponse({'success': True, 'message': 'Registro de Balanço deletado!'})


# --- VIEWS DE EXPORTAÇÃO (CSV E PDF) ---

@login_required
@admin_required
def exportar_jornada_csv(request):
    """ Exporta os dados da aba JORNADA (baseado nos filtros) para CSV/Excel. """
    filtro_tipo = request.GET.get('filtro_tipo', 'dia')
    usuario_id_filtro = request.GET.get('usuario_id')
    
    nome_arquivo = "jornada_export"
    registros = RegistroPonto.objects.none()
    query_base = RegistroPonto.objects.all().select_related('usuario', 'usuario__perfil')
    
    if usuario_id_filtro:
        try:
            usuario = User.objects.get(pk=usuario_id_filtro)
            query_base = query_base.filter(usuario=usuario)
            nome_arquivo = f"jornada_{usuario.username}"
        except User.DoesNotExist:
            pass
            
    if filtro_tipo == 'dia':
        data_filtro_str = request.GET.get('data', datetime.date.today().strftime('%Y-%m-%d'))
        try:
            data_filtro = datetime.datetime.strptime(data_filtro_str, '%Y-%m-%d').date()
            registros = query_base.filter(data=data_filtro)
            nome_arquivo += f"_{data_filtro_str}"
        except ValueError:
            registros = query_base.filter(data=datetime.date.today())
            nome_arquivo += f"_{datetime.date.today().strftime('%Y-%m-%d')}"
            
    elif filtro_tipo == 'mes':
        mes_filtro_str = request.GET.get('mes', datetime.date.today().strftime('%Y-%m'))
        try:
            mes_ano = datetime.datetime.strptime(mes_filtro_str, '%Y-%m').date()
            registros = query_base.filter(data__year=mes_ano.year, data__month=mes_ano.month)
            nome_arquivo += f"_{mes_filtro_str}"
        except ValueError:
            pass
            
    elif filtro_tipo == 'periodo':
        data_inicio_str = request.GET.get('data_inicio')
        data_fim_str = request.GET.get('data_fim')
        try:
            data_inicio = datetime.datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            data_fim = datetime.datetime.strptime(data_fim_str, '%Y-%m-%d').date()
            registros = query_base.filter(data__range=[data_inicio, data_fim])
            nome_arquivo += f"_{data_inicio_str}_a_{data_fim_str}"
        except (ValueError, TypeError):
            pass

    registros = registros.order_by('usuario__username', 'data', 'entrada')
    response = HttpResponse(content_type='text/csv', headers={'Content-Disposition': f'attachment; filename="{nome_arquivo}.csv"'})
    response.write(u'\ufeff'.encode('utf8')) 
    writer = csv.writer(response, delimiter=';') 
    writer.writerow([
        'Colaborador', 'Data', 'Tipo de Dia', 'Salario/Hora', 'Salario/Mes', 'Entrada', 'Saida Almoco', 'Retorno Almoco', 'Saida', 
        'Horas Almoco', 'Horas Trabalhadas', 'Horas Extras', 'Valor Receber (R$)'
    ])

    for r in registros:
        writer.writerow([
            r.usuario.username, r.data.strftime('%d/%m/%Y'), r.get_tipo_dia_display(),
            f"{r.usuario.perfil.valor_hora:.2f}".replace('.', ',') if r.usuario.perfil.valor_hora else 'N/A',
            f"{r.usuario.perfil.salario_mensal_bruto:.2f}".replace('.', ',') if r.usuario.perfil.salario_mensal_bruto else 'N/A',
            r.entrada.strftime('%H:%M') if r.entrada else '',
            r.saida_almoco.strftime('%H:%M') if r.saida_almoco else '',
            r.retorno_almoco.strftime('%H:%M') if r.retorno_almoco else '',
            r.saida.strftime('%H:%M') if r.saida else '',
            f"{r.horas_almoco:.2f}".replace('.', ','),
            f"{r.horas_trabalhadas:.2f}".replace('.', ','),
            f"{r.horas_extras:.2f}".replace('.', ','),
            f"{r.valor_receber:.2f}".replace('.', ',')
        ])
    return response

@login_required
@admin_required
def exportar_registro_pdf(request, pk):
    """
    Exporta um ÚNICO registro de ponto (PK) para um PDF.
    """
    try:
        registro = get_object_or_404(RegistroPonto, pk=pk)
        # (Verificação de segurança)
        if not (request.user.is_superuser or registro.usuario == request.user or request.user.groups.filter(name='Administradores').exists()):
             return HttpResponseForbidden("Acesso negado.")
                 
    except RegistroPonto.DoesNotExist:
        return HttpResponse("Registro não encontrado.", status=404)

    contexto = { 'registro': registro, }
    html_string = render_to_string('jornada/pdf_registro_ponto.html', contexto)
    pdf = HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf()
    filename = f"ponto_{registro.usuario.username}_{registro.data.strftime('%Y-%m-%d')}.pdf"
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response

@login_required
@admin_required
def exportar_jornada_pdf(request):
    """
    Exporta o RELATÓRIO COMPLETO (Mês/Período) de um usuário para PDF.
    """
    usuarios_trabalhando = User.objects.filter(perfil__esta_trabalhando=True)
    
    # --- 1. LÓGICA DE FILTRO ---
    filtro_tipo = request.GET.get('filtro_tipo', 'dia')
    usuario_id_filtro = request.GET.get('usuario_id')
    hoje_str = datetime.date.today().strftime('%Y-%m-%d')
    mes_str = datetime.date.today().strftime('%Y-%m')
    data_filtro_str = request.GET.get('data', hoje_str)
    mes_filtro_str = request.GET.get('mes', mes_str)
    data_inicio_str = request.GET.get('data_inicio', hoje_str)
    data_fim_str = request.GET.get('data_fim', hoje_str)

    usuario_selecionado = None
    if usuario_id_filtro and usuario_id_filtro.isdigit():
        usuario_selecionado = usuarios_trabalhando.filter(pk=int(usuario_id_filtro)).first()
    if not usuario_selecionado and usuarios_trabalhando.exists():
        usuario_selecionado = usuarios_trabalhando.first()

    registros = RegistroPonto.objects.none()
    if usuario_selecionado:
        query_base = RegistroPonto.objects.filter(usuario=usuario_selecionado)
        if filtro_tipo == 'dia':
            try:
                data_filtro = datetime.datetime.strptime(data_filtro_str, '%Y-%m-%d').date()
                registros = query_base.filter(data=data_filtro)
            except ValueError:
                registros = query_base.filter(data=datetime.date.today())
        elif filtro_tipo == 'mes':
            try:
                if not mes_filtro_str: mes_filtro_str = mes_str
                mes_ano = datetime.datetime.strptime(mes_filtro_str, '%Y-%m').date()
                registros = query_base.filter(data__year=mes_ano.year, data__month=mes_ano.month)
            except ValueError:
                pass
        elif filtro_tipo == 'periodo':
            try:
                data_inicio = datetime.datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
                data_fim = datetime.datetime.strptime(data_fim_str, '%Y-%m-%d').date()
                registros = query_base.filter(data__range=[data_inicio, data_fim])
            except ValueError:
                pass
    
    registros_list = registros.select_related('usuario__perfil').order_by('data')

    # --- 2. LÓGICA DE TOTAIS ---
    soma_horas_almoco = Decimal('0.0')
    soma_horas_trabalhadas = Decimal('0.0')
    soma_horas_extras = Decimal('0.0')
    soma_valor_receber = Decimal('0.0')
    for r in registros_list:
        soma_horas_almoco += r.horas_almoco
        soma_horas_trabalhadas += r.horas_trabalhadas
        soma_horas_extras += r.horas_extras
        soma_valor_receber += r.valor_receber

    # --- 3. CONTEXTO ---
    contexto = {
        'registros_todos': registros_list,
        'usuario_selecionado': usuario_selecionado,
        'filtro_tipo': filtro_tipo,
        'data_filtro': data_filtro_str,
        'mes_filtro': mes_filtro_str,
        'data_inicio': data_inicio_str,
        'data_fim': data_fim_str,
        'soma_horas_almoco': soma_horas_almoco,
        'soma_horas_trabalhadas': soma_horas_trabalhadas,
        'soma_horas_extras': soma_horas_extras,
        'soma_valor_receber': soma_valor_receber,
    }

    # --- 4. RENDERIZA O PDF ---
    html_string = render_to_string('jornada/pdf_jornada_relatorio.html', contexto)
    pdf = HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf()
    filename = f"relatorio_jornada_{usuario_selecionado.username}.pdf"
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


# ===================================================================
# === 2. VIEWS DE USUÁRIO COMUM ===
# ===================================================================

@login_required
def meu_trabalho_view(request):
    if not request.user.perfil.esta_trabalhando:
        messages.error(request, "Você não está configurado para o 'Modo Trabalho'.")
        return redirect('dashboard_usuario')
        
    registros = RegistroPonto.objects.filter(usuario=request.user)
    form_ponto = RegistroPontoForm(initial={'data': timezone.now().date()}) 
    hoje = timezone.localtime(timezone.now()).date()
    
    # Busca o ponto de hoje (que não seja Balanço)
    ponto_hoje = registros.filter(data=hoje).exclude(tipo_dia='BALANCO').first()

    total_horas = Decimal('0.0')
    total_extras = Decimal('0.0')
    total_receber = Decimal('0.0')
    mes_atual = datetime.date.today().month
    ano_atual = datetime.date.today().year
    
    # Soma apenas a Jornada Normal
    registros_mes = registros.filter(data__month=mes_atual, data__year=ano_atual)
    for r in registros_mes:
        total_horas += r.horas_trabalhadas
        total_extras += r.horas_extras
        total_receber += r.valor_receber
        
    # Adiciona os balanços do mês ao total
    balancos_mes = RegistroBalanço.objects.filter(
        usuario=request.user, 
        data__month=mes_atual, 
        data__year=ano_atual
    )
    # Adiciona 80 por balanço ao total a receber
    total_receber += (balancos_mes.count() * Decimal('80.00'))

    contexto = {
        'registros': registros.order_by('-data'), 
        'form_ponto': form_ponto, 'ponto_hoje': ponto_hoje,
        'total_horas_mes': total_horas, 'total_extras_mes': total_extras, 
        'total_receber_mes': total_receber,
    }
    return render(request, 'jornada/meu_trabalho.html', contexto)

# --- Ações AJAX para "Meu Trabalho" ---
@login_required
@require_POST
def bater_ponto_ajax(request):
    acao = request.POST.get('acao')
    agora_dt = timezone.localtime(timezone.now())
    hoje = agora_dt.date()
    horario_atual = agora_dt.time()
    
    tipo_dia_hoje = TipoDiaJornada.SABADO if hoje.weekday() == 5 else TipoDiaJornada.NORMAL
    
    # Lógica atualizada para get_or_create
    ponto, created = RegistroPonto.objects.get_or_create(
        usuario=request.user, 
        data=hoje,
        tipo_dia=tipo_dia_hoje 
    )

    try:
        if acao == 'entrada':
            if ponto.entrada: return JsonResponse({'success': False, 'message': 'Entrada já registrada.'}, status=400)
            ponto.entrada = horario_atual
        elif acao == 'saida_almoco':
            if ponto.saida_almoco: return JsonResponse({'success': False, 'message': 'Saída almoço já registrada.'}, status=400)
            ponto.saida_almoco = horario_atual
        elif acao == 'retorno_almoco':
            if ponto.retorno_almoco: return JsonResponse({'success': False, 'message': 'Retorno almoço já registrado.'}, status=400)
            ponto.retorno_almoco = horario_atual
        elif acao == 'saida':
            if ponto.saida: return JsonResponse({'success': False, 'message': 'Saída já registrada.'}, status=400)
            ponto.saida = horario_atual
        else:
            return JsonResponse({'success': False, 'message': 'Ação inválida.'}, status=400)
        ponto.save()
        return JsonResponse({'success': True, 'message': f'{acao.replace("_", " ").title()} registrada!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@require_POST
def registrar_ponto_ajax(request):
    """ Usuário comum registra um ponto (Jornada) """
    form = RegistroPontoForm(request.POST)
    if form.is_valid():
        try:
            ponto = form.save(commit=False)
            ponto.usuario = request.user
            ponto.save()
            return JsonResponse({'success': True})
        except IntegrityError:
            return JsonResponse({'success': False, 'message': 'Já existe um registro deste tipo para esta data.'}, status=400)
        except Exception:
            return JsonResponse({'success': False, 'message': 'Erro ao salvar o registro.'}, status=400)
    return JsonResponse({'success': False, 'errors': json.loads(form.errors.as_json())}, status=400)

@login_required
def get_ponto_json(request, pk):
    """ Usuário comum busca seu próprio registro de JORNADA """
    try:
        ponto = get_object_or_404(RegistroPonto, pk=pk, usuario=request.user)
        data = {
            'data': ponto.data.strftime('%Y-%m-%d'),
            'tipo_dia': ponto.tipo_dia,
            'entrada': ponto.entrada.strftime('%H:%M') if ponto.entrada else '', 
            'saida_almoco': ponto.saida_almoco.strftime('%H:%M') if ponto.saida_almoco else '', 
            'retorno_almoco': ponto.retorno_almoco.strftime('%H:%M') if ponto.retorno_almoco else '', 
            'saida': ponto.saida.strftime('%H:%M') if ponto.saida else '',
            'atestado_cid': ponto.atestado_cid,
            'atestado_crm': ponto.atestado_crm,
            'atestado_obs': ponto.atestado_obs,
        }
        return JsonResponse(data)
    except RegistroPonto.DoesNotExist:
        return HttpResponseForbidden("Acesso negado")

@login_required
@require_POST
def editar_ponto_ajax(request, pk):
    """ Usuário comum edita seu próprio registro de JORNADA """
    try:
        ponto = get_object_or_404(RegistroPonto, pk=pk, usuario=request.user)
        form = RegistroPontoForm(request.POST, instance=ponto)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'errors': json.loads(form.errors.as_json())}, status=400)
    except RegistroPonto.DoesNotExist:
        return HttpResponseForbidden("Acesso negado")

@login_required
@require_POST
def deletar_ponto_ajax(request, pk):
    """ Usuário comum deleta seu próprio registro de JORNADA """
    try:
        ponto = get_object_or_404(RegistroPonto, pk=pk, usuario=request.user)
        ponto.delete()
        return JsonResponse({'success': True})
    except RegistroPonto.DoesNotExist:
        return HttpResponseForbidden("Acesso negado")


# --- 2B. PÁGINA "MEUS ESTUDOS" ---
@login_required
def meus_estudos_view(request):
    if not request.user.perfil.esta_estudando:
        messages.error(request, "Você não está configurado para o 'Modo Estudo'.")
        return redirect('dashboard_usuario')
    materias = Materia.objects.filter(usuario=request.user).prefetch_related('notas').order_by('nome')
    form_materia = MateriaForm()
    form_nota = NotaForm(usuario=request.user) 
    contexto = {'materias': materias, 'form_materia': form_materia, 'form_nota': form_nota}
    return render(request, 'jornada/meus_estudos.html', contexto)

@login_required
@require_POST
def adicionar_materia_ajax(request):
    form = MateriaForm(request.POST)
    if form.is_valid():
        try:
            materia = form.save(commit=False)
            materia.usuario = request.user
            materia.save()
            return JsonResponse({'success': True, 'materia_id': materia.id, 'materia_nome': materia.nome})
        except Exception: 
            return JsonResponse({'success': False, 'message': 'Matéria já cadastrada.'}, status=400)
    return JsonResponse({'success': False, 'errors': json.loads(form.errors.as_json())}, status=400)

@login_required
@require_POST
def adicionar_nota_ajax(request):
    form = NotaForm(request.POST, usuario=request.user)
    if form.is_valid():
        form.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'errors': json.loads(form.errors.as_json())}, status=400)

@login_required
@require_POST
def deletar_materia_ajax(request, pk):
    try:
        materia = get_object_or_404(Materia, pk=pk, usuario=request.user)
        materia.delete()
        return JsonResponse({'success': True})
    except Materia.DoesNotExist:
        return HttpResponseForbidden("Acesso negado")

@login_required
@require_POST
def deletar_nota_ajax(request, pk):
    try:
        nota = get_object_or_404(Nota, pk=pk, materia__usuario=request.user)
        nota.delete()
        return JsonResponse({'success': True})
    except Nota.DoesNotExist:
        return HttpResponseForbidden("Acesso negado")