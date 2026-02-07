import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q, Sum, Value, DecimalField, Avg
from django.db.models.functions import Coalesce

# --- Imports de Autenticação e Mensagens ---
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages

# Imports dos seus outros aplicativos
from .models import Perfil

# Importação dos Modelos de Estoque
from estoque.models import Estoque, Comodo, ItemCasa, ItemPet, ItemUsuario

# Finanças
from financas.models import Financa 

# Rotinas
from rotinas.models import RotinaPadrao, TarefaDiaria, HistoricoCastigo, FechamentoMensal

# --- ALIMENTAÇÃO (NOVO IMPORT) ---
from alimentacao.models import Refeicao

# Core
from core.models import Pet
from core.decorators import admin_required 

# Dicionário para traduzir o dia da semana
DIAS_SEMANA_DJANGO = { 
    0: 'Segunda-feira', 
    1: 'Terça-feira', 
    2: 'Quarta-feira', 
    3: 'Quinta-feira', 
    4: 'Sexta-feira', 
    5: 'Sábado', 
    6: 'Domingo' 
}

# ===================================================================
# === 1. VIEWS DE AUTENTICAÇÃO E REDIRECIONAMENTO (CORE) ===
# ===================================================================

def logar_usuario(request):
    if request.user.is_authenticated:
        return redirect('redirecionar_usuario')

    if request.method == 'POST':
        usuario_form = request.POST.get('username')
        senha_form = request.POST.get('password')

        user = authenticate(request, username=usuario_form, password=senha_form)

        if user is not None:
            login(request, user)
            messages.success(request, f'Login realizado com sucesso. Bem-vindo, {user.username}!')
            return redirect('redirecionar_usuario')
        else:
            messages.error(request, 'Usuário ou senha inválidos. Tente novamente.')
            return redirect('login') 

    return render(request, 'login.html')


def deslogar_usuario(request):
    logout(request)
    messages.info(request, 'Você foi desconectado.')
    return redirect('login')


@login_required 
def redirecionar_usuario(request):
    if request.user.is_superuser:
        return redirect('dashboard_admin')
    
    if request.user.groups.filter(name='Administradores').exists():
        return redirect('dashboard_admin')
    
    if request.user.groups.filter(name='Usuarios_Comuns').exists():
        return redirect('dashboard_usuario')

    messages.warning(request, "Seu perfil de usuário não está associado a um grupo específico. Você foi redirecionado para o dashboard padrão.")
    return redirect('dashboard_usuario')


# ===================================================================
# === 2. VIEWS DE GESTÃO (ADMINISTRADORES / SUPER USERS) ===
# ===================================================================

@login_required
@admin_required
def dashboard_admin(request):
    """
    View principal do Dashboard de Gestão (Admin/CEO).
    """
    all_users = User.objects.all().order_by('username')
    all_pets = Pet.objects.all().order_by('nome_pet')
    all_casas = Comodo.objects.all().order_by('nome')
    
    filtro_opcoes = [{'id': f'user_{u.id}', 'text': f'Usuário: {u.username}'} for u in all_users]
    filtro_opcoes.extend([{'id': f'pet_{p.id}', 'text': f'Pet: {p.nome_pet}'} for p in all_pets])
    filtro_opcoes.extend([{'id': f'casa_{c.id}', 'text': f'Casa: {c.nome}'} for c in all_casas])
    
    # --- Cálculos Iniciais (Sem filtros) ---
    total_entidades = all_users.count() + all_pets.count() + all_casas.count()
    
    # Estoque
    qtd_casa = ItemCasa.objects.aggregate(t=Coalesce(Sum('quantidade'), Value(0, output_field=DecimalField())))['t']
    qtd_pet = ItemPet.objects.aggregate(t=Coalesce(Sum('quantidade'), Value(0, output_field=DecimalField())))['t']
    qtd_user = ItemUsuario.objects.aggregate(t=Coalesce(Sum('quantidade'), Value(0, output_field=DecimalField())))['t']
    total_itens_estoque = qtd_casa + qtd_pet + qtd_user

    # Finanças
    receitas = Financa.objects.filter(tipo='Receitas').aggregate(total=Coalesce(Sum('valor'), Value(0.0, output_field=DecimalField())))['total']
    despesas = Financa.objects.filter(tipo='Despesas').aggregate(total=Coalesce(Sum('valor'), Value(0.0, output_field=DecimalField())))['total']
    saldo_financeiro = receitas - despesas
    
    # Rotinas e Alimentação (Hoje)
    hoje = datetime.date.today()
    total_tarefas_rotina = TarefaDiaria.objects.filter(data_tarefa=hoje).count()

    # --- Lógica de Alimentação (Média Global de Hoje) ---
    # Soma todas as calorias de todas as refeições de hoje
    refeicoes_hoje = Refeicao.objects.filter(data=hoje)
    total_calorias_hoje = sum(r.total_calorias for r in refeicoes_hoje)
    
    # Conta quantos usuários registraram refeição hoje
    qtd_usuarios_ativos_nutri = refeicoes_hoje.values('usuario').distinct().count()
    
    media_calorias_hoje = 0
    if qtd_usuarios_ativos_nutri > 0:
        media_calorias_hoje = int(total_calorias_hoje / qtd_usuarios_ativos_nutri)

    contexto = {
        'filtro_opcoes': filtro_opcoes,
        'total_usuarios': total_entidades,
        'total_itens_estoque': total_itens_estoque,
        'saldo_financeiro': f'{saldo_financeiro:0.2f}'.replace('.', ','),
        'total_tarefas_rotina': total_tarefas_rotina,
        'media_calorias_hoje': media_calorias_hoje, # Novo
    }
    return render(request, 'dashboard_admin.html', contexto)


@login_required
@admin_required
def update_dashboard_counts(request):
    """
    View AJAX para atualizar os cards do dashboard_admin (Filtros).
    """
    selected_ids = request.GET.getlist('selecao[]')
    user_ids = [int(sid.replace('user_', '')) for sid in selected_ids if sid.startswith('user_')]
    pet_ids = [int(sid.replace('pet_', '')) for sid in selected_ids if sid.startswith('pet_')]
    casa_ids = [int(sid.replace('casa_', '')) for sid in selected_ids if sid.startswith('casa_')]
    hoje = datetime.date.today()
    
    # Variáveis de retorno
    total_itens_estoque = 0
    saldo_financeiro = 0
    total_tarefas_rotina = 0
    media_calorias = 0 # Novo

    if not selected_ids:
        # --- TOTAIS GERAIS (Sem Filtro) ---
        total_entidades = User.objects.count() + Pet.objects.count() + Comodo.objects.count()
        
        # Estoque
        qc = ItemCasa.objects.aggregate(t=Coalesce(Sum('quantidade'), Value(0, output_field=DecimalField())))['t']
        qp = ItemPet.objects.aggregate(t=Coalesce(Sum('quantidade'), Value(0, output_field=DecimalField())))['t']
        qu = ItemUsuario.objects.aggregate(t=Coalesce(Sum('quantidade'), Value(0, output_field=DecimalField())))['t']
        total_itens_estoque = qc + qp + qu
        
        # Finanças
        receitas = Financa.objects.aggregate(total=Coalesce(Sum('valor', filter=Q(tipo='Receitas')), Value(0.0, output_field=DecimalField())))['total']
        despesas = Financa.objects.aggregate(total=Coalesce(Sum('valor', filter=Q(tipo='Despesas')), Value(0.0, output_field=DecimalField())))['total']
        saldo_financeiro = receitas - despesas
        
        # Rotinas
        total_tarefas_rotina = TarefaDiaria.objects.filter(data_tarefa=hoje).count()

        # Alimentação (Global)
        refeicoes = Refeicao.objects.filter(data=hoje)
        total_cal = sum(r.total_calorias for r in refeicoes)
        usuarios_ativos = refeicoes.values('usuario').distinct().count()
        if usuarios_ativos > 0:
            media_calorias = int(total_cal / usuarios_ativos)

    else:
        # --- TOTAIS FILTRADOS ---
        total_entidades = len(user_ids) + len(pet_ids) + len(casa_ids)
        
        # Estoque Filtrado
        qc = 0; qp = 0; qu = 0
        if casa_ids:
            qc = ItemCasa.objects.filter(comodo_id__in=casa_ids).aggregate(t=Coalesce(Sum('quantidade'), Value(0, output_field=DecimalField())))['t']
        if pet_ids:
            qp = ItemPet.objects.filter(pet_id__in=pet_ids).aggregate(t=Coalesce(Sum('quantidade'), Value(0, output_field=DecimalField())))['t']
        if user_ids:
            qu = ItemUsuario.objects.filter(usuario_id__in=user_ids).aggregate(t=Coalesce(Sum('quantidade'), Value(0, output_field=DecimalField())))['t']
            
        total_itens_estoque = qc + qp + qu

        # Finanças (Filtro por usuário)
        if user_ids:
            receitas = Financa.objects.filter(usuario_id__in=user_ids, tipo='Receitas').aggregate(total=Coalesce(Sum('valor'), Value(0.0, output_field=DecimalField())))['total']
            despesas = Financa.objects.filter(usuario_id__in=user_ids, tipo='Despesas').aggregate(total=Coalesce(Sum('valor'), Value(0.0, output_field=DecimalField())))['total']
            saldo_financeiro = receitas - despesas
        else:
            saldo_financeiro = 0 

        # Rotinas (Filtro por usuário)
        if user_ids:
            total_tarefas_rotina = TarefaDiaria.objects.filter(usuario_id__in=user_ids, data_tarefa=hoje).count()
        else:
            total_tarefas_rotina = 0

        # Alimentação (Filtro por usuário)
        if user_ids:
            refeicoes = Refeicao.objects.filter(usuario_id__in=user_ids, data=hoje)
            total_cal = sum(r.total_calorias for r in refeicoes)
            # Se for 1 usuário, mostra o total dele. Se forem vários, mostra média.
            qtd_filtrada = len(user_ids)
            # Para ser mais preciso: dividir pelo número de usuários que REALMENTE comeram ou pelo total filtrado?
            # Vamos dividir pelo número de usuários filtrados que tiveram registros.
            usuarios_ativos = refeicoes.values('usuario').distinct().count()
            
            if usuarios_ativos > 0:
                media_calorias = int(total_cal / usuarios_ativos)
        else:
            media_calorias = 0

    data = {
        'total_usuarios': total_entidades,
        'total_itens_estoque': total_itens_estoque,
        'saldo_financeiro': f'{saldo_financeiro:0.2f}'.replace('.', ','),
        'total_tarefas_rotina': total_tarefas_rotina,
        'media_calorias': f"{media_calorias} kcal", # Novo Campo JSON
    }
    return JsonResponse(data)


# --- Funções Parciais para Modais do DASHBOARD ADMIN ---

def _get_ids_from_selecao(selecao):
    user_ids = [int(sid.replace('user_', '')) for sid in selecao if sid.startswith('user_')]
    pet_ids = [int(sid.replace('pet_', '')) for sid in selecao if sid.startswith('pet_')]
    casa_ids = [int(sid.replace('casa_', '')) for sid in selecao if sid.startswith('casa_')]
    return user_ids, pet_ids, casa_ids

@login_required
@admin_required 
def tabela_usuarios_partial(request):
    dados = request.POST if request.method == 'POST' else request.GET
    selecao = dados.getlist('selecao[]')
    perfis = Perfil.objects.select_related('usuario').all()
    if selecao:
        user_ids, _, _ = _get_ids_from_selecao(selecao)
        perfis = perfis.filter(usuario_id__in=user_ids)
    contexto = {'perfis': perfis.order_by('usuario__id')}
    return render(request, 'partials/_tabela_usuarios.html', contexto)

@login_required
@admin_required
def tabela_estoque_partial(request):
    selecao = request.GET.getlist('selecao[]')
    itens_estoque = Estoque.objects.select_related(
        'item_casa', 'item_casa__comodo', 'item_casa__categoria',
        'item_pet', 'item_pet__pet',
        'item_usuario', 'item_usuario__usuario'
    ).all()
    
    if selecao:
        user_ids, pet_ids, casa_ids = _get_ids_from_selecao(selecao)
        itens_estoque = itens_estoque.filter(
            Q(item_usuario__usuario_id__in=user_ids) | 
            Q(item_pet__pet_id__in=pet_ids) | 
            Q(item_casa__comodo_id__in=casa_ids)
        )
    contexto = {'itens_estoque': itens_estoque.order_by('setor', 'id')}
    return render(request, 'partials/_tabela_estoque.html', contexto)

@login_required
@admin_required
def tabela_financas_partial(request):
    selecao = request.GET.getlist('selecao[]')
    lancamentos = Financa.objects.select_related('usuario', 'conta', 'categoria').all()
    if selecao:
        user_ids, _, _ = _get_ids_from_selecao(selecao)
        lancamentos = lancamentos.filter(usuario_id__in=user_ids)
    contexto = {'lancamentos': lancamentos.order_by('-data_registro')}
    return render(request, 'partials/_tabela_financas.html', contexto)

@login_required
@admin_required
def tabela_rotinas_partial(request):
    selecao = request.GET.getlist('selecao[]')
    hoje = datetime.date.today()
    tarefas = TarefaDiaria.objects.filter(data_tarefa=hoje).select_related('rotina', 'usuario')
    if selecao:
        user_ids, _, _ = _get_ids_from_selecao(selecao)
        tarefas = tarefas.filter(usuario_id__in=user_ids)
    contexto = {'tarefas_de_hoje': tarefas.order_by('usuario__username', 'prazo_hora')}
    return render(request, 'partials/_tabela_rotinas.html', contexto)


# ===================================================================
# === 3. VIEWS DE USUÁRIO COMUM ===
# ===================================================================

@login_required
def dashboard_usuario(request):
    usuario_logado = request.user
    hoje = datetime.date.today()

    # Finanças
    receitas_usuario = Financa.objects.filter(
        usuario=usuario_logado, tipo='Receitas'
    ).aggregate(total=Coalesce(Sum('valor'), Value(0.0, output_field=DecimalField())))['total']
    despesas_usuario = Financa.objects.filter(
        usuario=usuario_logado, tipo='Despesas'
    ).aggregate(total=Coalesce(Sum('valor'), Value(0.0, output_field=DecimalField())))['total']
    saldo_financeiro_usuario = receitas_usuario - despesas_usuario

    # Estoque
    total_itens_estoque_usuario = ItemUsuario.objects.filter(
        usuario=usuario_logado
    ).aggregate(total=Coalesce(Sum('quantidade'), Value(0.0, output_field=DecimalField())))['total']

    # Rotinas e Pontos
    tarefas_hoje_usuario = TarefaDiaria.objects.filter(
        usuario=usuario_logado, data_tarefa=hoje
    ).count()
    
    pts_tarefas = TarefaDiaria.objects.filter(usuario=usuario_logado, status='CONCLUIDO').aggregate(t=Coalesce(Sum('pontos_ganhos'), Value(0)))['t']
    
    castigos_ativos_usuario = HistoricoCastigo.objects.filter(
        usuario=usuario_logado, cumprido=False
    ).count()

    # Pets
    pets_usuario = 0
    if hasattr(Pet, 'usuario'): 
        pets_usuario = Pet.objects.filter(usuario=usuario_logado).count() 

    contexto = {
        'saldo_financeiro_usuario': f'{saldo_financeiro_usuario:0.2f}'.replace('.', ','),
        'total_itens_estoque_usuario': total_itens_estoque_usuario,
        'tarefas_hoje_usuario': tarefas_hoje_usuario,
        'pontuacao_usuario': pts_tarefas, 
        'castigos_ativos_usuario': castigos_ativos_usuario,
        'pets_usuario': pets_usuario,
    }
    return render(request, 'dashboard_usuario.html', contexto)