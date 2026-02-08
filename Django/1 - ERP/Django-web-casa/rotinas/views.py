from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.models import User
from datetime import datetime

from .models import RotinaPadrao, TarefaDiaria, HistoricoCastigo
from .forms import CriarTarefaForm, AplicarCastigoForm

# --- MOTOR DE GERAÇÃO AUTOMÁTICA ---
def gerar_tarefas_do_dia(usuario):
    """
    Verifica se existem tarefas rotineiras para hoje e as cria se não existirem.
    """
    hoje = timezone.now().date()
    dia_python = str(hoje.weekday()) # 0=Segunda, ..., 6=Domingo
    
    rotinas = RotinaPadrao.objects.filter(ativa=True, usuarios_padrao=usuario)
    
    cnt = 0
    for rotina in rotinas:
        dias = rotina.dias_recorrencia # Ex: 'ALL' ou '0,2,4'
        
        # Verifica se deve criar hoje (Se é dia de recorrência ou Todos os dias)
        if 'ALL' in dias or dia_python in dias:
            obj, created = TarefaDiaria.objects.get_or_create(
                rotina=rotina,
                usuario=usuario,
                data_tarefa=hoje,
                defaults={
                    'prazo_hora': rotina.horario_sugerido,
                    'status': 'PENDENTE',
                    'pontos_ganhos': 0
                }
            )
            if created: cnt += 1
    return cnt

# --- DASHBOARD PRINCIPAL (AUDITORIA) ---
@login_required
def gerenciar_rotinas(request):
    # 1. Filtro de Data
    data_str = request.GET.get('data')
    try:
        data_filtro = datetime.strptime(data_str, '%Y-%m-%d').date() if data_str else timezone.now().date()
    except ValueError:
        data_filtro = timezone.now().date()

    # 2. Filtro de Usuários (Lista Múltipla)
    usuarios_filtro_ids = request.GET.getlist('usuario_filtro') 
    # Converte string '1' para int 1, ignorando lixo
    usuarios_selecionados = [int(uid) for uid in usuarios_filtro_ids if uid.isdigit()]

    is_admin = request.user.is_superuser or request.user.groups.filter(name='Administradores').exists()

    # Motor de Geração (Garante que tarefas de hoje existam para os usuários)
    if data_filtro == timezone.now().date():
        alvos = User.objects.exclude(is_superuser=True) if is_admin else [request.user]
        for u in alvos:
            gerar_tarefas_do_dia(u)

    # === PREPARAÇÃO DAS QUERIES ===
    
    # Base: Lista de usuários para o dropdown (apenas Admin vê)
    todos_usuarios = User.objects.exclude(is_superuser=True).order_by('username') if is_admin else []

    # Query 1: Tarefas do Dia (Aba Linha do Tempo)
    # IMPORTANTE: A ordenação aqui define o desenho da tela.
    # 1º Por Hora (prazo_hora) -> Para agrupar na bolinha do tempo.
    # 2º Por Rotina (rotina__nome) -> Para agrupar no Card da Tarefa.
    # 3º Por Usuário -> Para listar alfabeticamente dentro do card.
    tarefas = TarefaDiaria.objects.filter(data_tarefa=data_filtro)\
        .select_related('rotina', 'usuario')\
        .order_by('prazo_hora', 'rotina__nome', 'usuario__username')

    # Query 2: Histórico de Castigos (Base para Aba Disciplina e Aba Histórico)
    hist_castigos_query = HistoricoCastigo.objects.all().order_by('-data_ocorrencia')

    # Query 3: Histórico de Tarefas (Para a nova Aba Histórico Geral)
    # Traz as últimas 50 tarefas processadas (Concluídas ou Não Feitas)
    hist_tarefas_query = TarefaDiaria.objects.exclude(status='PENDENTE')\
        .select_related('rotina', 'usuario').order_by('-data_tarefa', '-prazo_hora')[:50]

    # === APLICAÇÃO DOS FILTROS (SEGURANÇA E SELEÇÃO) ===
    
    if not is_admin:
        # Usuário Comum: Vê apenas os seus dados
        tarefas = tarefas.filter(usuario=request.user)
        hist_castigos_query = hist_castigos_query.filter(usuario=request.user)
        hist_tarefas_query = hist_tarefas_query.filter(usuario=request.user)
    
    elif usuarios_selecionados:
        # Admin com Filtro Ativo: Filtra todas as listas pelos IDs selecionados
        tarefas = tarefas.filter(usuario_id__in=usuarios_selecionados)
        hist_castigos_query = hist_castigos_query.filter(usuario_id__in=usuarios_selecionados)
        hist_tarefas_query = hist_tarefas_query.filter(usuario_id__in=usuarios_selecionados)

    # === PROCESSAMENTO FINAL ===
    
    # Dados para a aba Disciplina
    castigos_ativos = hist_castigos_query.filter(cumprido=False)
    historico_castigos_recente = hist_castigos_query[:10]

    context = {
        # Dados de Controle
        'is_admin': is_admin,
        'data_atual': data_filtro.strftime('%Y-%m-%d'),
        'todos_usuarios': todos_usuarios,
        'usuarios_selecionados': usuarios_selecionados,

        # Aba 1: Tarefas (Timeline)
        'tarefas': tarefas,
        
        # Aba 2: Disciplina
        'castigos_ativos': castigos_ativos,
        'historico_castigos_recente': historico_castigos_recente,

        # Aba 3: Histórico Completo
        'historico_tarefas_completo': hist_tarefas_query,
        'historico_castigos_completo': hist_castigos_query[:50],

        # Formulários
        'form_criar': CriarTarefaForm(initial={'data_tarefa': data_filtro}),
        'form_castigo': AplicarCastigoForm(),
    }
    return render(request, 'rotinas/gerenciar_rotinas.html', context)


# --- FUNCIONALIDADE: CLONAR ROTINA (IMPORTAR) ---
@login_required
@require_POST
def importar_rotina_passada(request):
    if not request.user.is_superuser:
        return redirect('rotinas:gerenciar_rotinas')

    data_origem_str = request.POST.get('data_origem')
    data_destino_str = request.POST.get('data_destino')
    usuario_alvo_id = request.POST.get('usuario_alvo')

    try:
        data_origem = datetime.strptime(data_origem_str, '%Y-%m-%d').date()
        data_destino = datetime.strptime(data_destino_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        messages.error(request, "Datas inválidas.")
        return redirect('rotinas:gerenciar_rotinas')

    # Busca as tarefas originais
    tarefas_origem = TarefaDiaria.objects.filter(data_tarefa=data_origem)

    # Filtra se não for "Todos"
    if usuario_alvo_id and usuario_alvo_id != 'todos':
        tarefas_origem = tarefas_origem.filter(usuario_id=usuario_alvo_id)

    if not tarefas_origem.exists():
        messages.warning(request, f"Nenhuma tarefa em {data_origem.strftime('%d/%m')} para copiar.")
        return redirect(f"{reverse('rotinas:gerenciar_rotinas')}?data={data_destino_str}")

    count = 0
    with transaction.atomic():
        for t in tarefas_origem:
            # Clona a tarefa para o dia de destino, resetando status
            obj, created = TarefaDiaria.objects.get_or_create(
                rotina=t.rotina,
                usuario=t.usuario,
                data_tarefa=data_destino,
                defaults={
                    'prazo_hora': t.prazo_hora,
                    'pontos_extra': 0,
                    'status': 'PENDENTE',
                    'observacao_admin': '', 
                    'pontos_ganhos': 0,
                    'data_conclusao': None
                }
            )
            if created: count += 1

    if count > 0:
        messages.success(request, f"{count} tarefas clonadas com sucesso!")
    else:
        messages.info(request, "Tarefas já existem no destino.")

    return redirect(f"{reverse('rotinas:gerenciar_rotinas')}?data={data_destino_str}")


# --- AÇÕES DE CRIAÇÃO E EDIÇÃO (AJAX/POST) ---

@login_required
@require_POST
def criar_tarefa_massa(request):
    if not request.user.is_superuser: return redirect('rotinas:gerenciar_rotinas')
    
    form = CriarTarefaForm(request.POST)
    if form.is_valid():
        rotina = form.cleaned_data['rotina']
        usuarios = form.cleaned_data['usuarios'] # Lista de Users (graças ao ModelMultipleChoiceField)
        data = form.cleaned_data['data_tarefa']
        prazo = form.cleaned_data['prazo_hora']
        pontos = form.cleaned_data['pontos_extra_inicial'] or 0
        
        count = 0
        for u in usuarios:
            obj, created = TarefaDiaria.objects.get_or_create(
                rotina=rotina, usuario=u, data_tarefa=data,
                defaults={'prazo_hora': prazo, 'pontos_extra': pontos, 'status': 'PENDENTE'}
            )
            if created: count += 1
        messages.success(request, f"{count} tarefas criadas!")
    else:
        messages.error(request, "Erro ao criar tarefas. Verifique os campos.")
        
    return redirect('rotinas:gerenciar_rotinas')

@login_required
def atualizar_status_ajax(request, pk):
    """
    Alterna o status via clique simples (Toggle)
    """
    tarefa = get_object_or_404(TarefaDiaria, pk=pk)
    if not request.user.is_superuser and tarefa.usuario != request.user:
        return JsonResponse({'success': False})
    
    status_solicitado = request.GET.get('status')
    
    # Se o admin mandou um status específico (ex: NAO_FEITO pelo modal), usa ele.
    if status_solicitado:
        tarefa.status = status_solicitado
        if status_solicitado == 'CONCLUIDO':
            tarefa.data_conclusao = timezone.now()
        else:
            tarefa.data_conclusao = None
    else:
        # Lógica de toggle padrão (se não vier status na URL)
        if tarefa.status == 'CONCLUIDO':
            tarefa.status = 'PENDENTE'
            tarefa.data_conclusao = None
        else:
            tarefa.status = 'CONCLUIDO'
            tarefa.data_conclusao = timezone.now()
    
    tarefa.save()
    return JsonResponse({'success': True, 'pontos': tarefa.pontos_ganhos, 'novo_status': tarefa.status})

@login_required
@require_POST
def aplicar_castigo(request):
    if not request.user.is_superuser: return redirect('rotinas:gerenciar_rotinas')
    
    form = AplicarCastigoForm(request.POST)
    if form.is_valid():
        c = form.save(commit=False)
        c.aplicado_por = request.user
        c.save()
        messages.warning(request, f"Punição registrada para {c.usuario.username}")
    else:
        msg = next(iter(form.errors.values()))[0]
        messages.error(request, f"Erro: {msg}")
    return redirect('rotinas:gerenciar_rotinas')

@login_required
def liberar_castigo(request, pk):
    if not request.user.is_superuser: return redirect('rotinas:gerenciar_rotinas')
    c = get_object_or_404(HistoricoCastigo, pk=pk)
    c.cumprido = True
    c.save()
    messages.success(request, f"Castigo de {c.usuario.username} finalizado.")
    return redirect('rotinas:gerenciar_rotinas')

@login_required
@require_POST
def admin_editar_tarefa(request, pk):
    """
    Edição avançada (Status, Obs, Pontos) via Modal ou Javascript
    """
    if not request.user.is_superuser: return JsonResponse({'success': False})
    
    tarefa = get_object_or_404(TarefaDiaria, pk=pk)
    
    # Atualiza apenas o que foi enviado
    if 'status' in request.POST:
        tarefa.status = request.POST.get('status')
    if 'pontos_extra' in request.POST:
        tarefa.pontos_extra = request.POST.get('pontos_extra')
    if 'observacao_admin' in request.POST:
        tarefa.observacao_admin = request.POST.get('observacao_admin')
        
    tarefa.save()
    return JsonResponse({'success': True})

@login_required
def get_ultimo_castigo_ajax(request):
    uid = request.GET.get('user_id')
    ultimo = HistoricoCastigo.objects.filter(usuario_id=uid).order_by('-data_ocorrencia').first()
    if ultimo:
        return JsonResponse({
            'existe': True,
            'motivo': ultimo.motivo,
            'pontos': ultimo.pontos_perdidos,
            'gravidade': ultimo.get_gravidade_display(),
            'data': ultimo.data_ocorrencia.strftime('%d/%m')
        })
    return JsonResponse({'existe': False})