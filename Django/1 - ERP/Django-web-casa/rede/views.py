from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import Dispositivo
from .forms import DispositivoForm
import paramiko # Biblioteca para conexão SSH

# --- CONFIGURAÇÕES DO ROTEADOR (MIKROTIK) ---
# Idealmente, mova isso para o settings.py em produção
ROUTER_IP = '192.168.88.1'  # IP do seu Mikrotik
ROUTER_PORT = 22
ROUTER_USER = 'admin'
ROUTER_PASS = 'sua_senha_aqui'

def aplicar_regras_firewall():
    """
    Conecta no Roteador via SSH e atualiza as regras de bloqueio.
    Lógica: Apaga regras antigas criadas pelo Django e cria novas para quem está bloqueado.
    """
    # 1. Busca dispositivos que devem ser bloqueados
    bloqueados_manual = Dispositivo.objects.filter(status='BLOQUEADO')
    
    # Busca dispositivos em castigo (cujo tempo ainda não acabou)
    castigo_ativo = Dispositivo.objects.filter(
        status='CASTIGO', 
        castigo_ate__gt=timezone.now()
    )
    
    # Junta as listas (sem duplicatas)
    lista_para_bloquear = list(bloqueados_manual) + list(castigo_ativo)
    lista_para_bloquear = list(set(lista_para_bloquear)) # Remove duplicados se houver

    print(f"--- FIREWALL: Bloqueando {len(lista_para_bloquear)} dispositivos ---")

    # 2. Conexão SSH
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(ROUTER_IP, port=ROUTER_PORT, username=ROUTER_USER, password=ROUTER_PASS, timeout=5)
        
        # 3. Limpeza: Remove regras antigas criadas por nós (identificadas pelo comentário)
        # Comando Mikrotik: remove regras onde o comentário é "DJANGO_BLOCK"
        cmd_limpar = '/ip firewall filter remove [find comment="DJANGO_BLOCK"]'
        client.exec_command(cmd_limpar)

        # 4. Aplicação: Cria uma regra de DROP para cada MAC
        for device in lista_para_bloquear:
            mac = device.mac_address
            if len(mac) == 17: # Validação básica
                # Comando Mikrotik: Bloqueia Forward (Internet) para este MAC
                # Coloca no topo (place-before=0) para garantir que funcione antes de regras de 'accept'
                cmd_bloqueio = f'/ip firewall filter add chain=forward src-mac-address={mac} action=drop comment="DJANGO_BLOCK" place-before=0'
                client.exec_command(cmd_bloqueio)
                print(f"Bloqueado: {device.nome} [{mac}]")

        client.close()
        return True

    except Exception as e:
        print(f"ERRO SSH ROTEADOR: {e}")
        # Não quebra o site se o roteador estiver offline, apenas loga o erro
        return False

# =================================================================
# VIEWS (MANTIDAS IGUAIS, APENAS CHAMAM A FUNÇÃO ACIMA)
# =================================================================

@login_required
def gerenciar_rede(request):
    dispositivos = Dispositivo.objects.all().order_by('usuario', 'nome')
    form = DispositivoForm()
    
    # Verifica status de castigo e atualiza visualmente se expirou
    # (Opcional: limpa o status no banco se o tempo já passou para manter consistência)
    for d in dispositivos:
        if d.status == 'CASTIGO' and d.castigo_ate and d.castigo_ate < timezone.now():
            d.status = 'LIBERADO'
            d.save()

    bloqueados_count = sum(1 for d in dispositivos if d.esta_bloqueado)
    
    context = {
        'dispositivos': dispositivos,
        'form': form,
        'bloqueados_count': bloqueados_count
    }
    return render(request, 'rede/gerenciar_rede.html', context)

@login_required
@require_POST
def salvar_dispositivo(request):
    form = DispositivoForm(request.POST)
    if form.is_valid():
        form.save()
        # Aplica regras imediatamente ao salvar (caso já nasça bloqueado)
        aplicar_regras_firewall()
        return JsonResponse({'success': True, 'message': 'Dispositivo cadastrado!'})
    return JsonResponse({'success': False, 'errors': form.errors.as_json()}, status=400)

@login_required
@require_POST
def alternar_bloqueio(request, pk):
    """Botão rápido de Bloquear/Liberar"""
    device = get_object_or_404(Dispositivo, pk=pk)
    
    if device.status == 'LIBERADO':
        device.status = 'BLOQUEADO'
        msg = 'Dispositivo BLOQUEADO na rede!'
    else:
        device.status = 'LIBERADO'
        device.castigo_ate = None # Limpa horário de castigo
        msg = 'Dispositivo LIBERADO!'
    
    device.save()
    
    # Chama o SSH para aplicar no roteador
    sucesso_ssh = aplicar_regras_firewall()
    
    if not sucesso_ssh:
        msg += " (Aviso: Erro ao conectar no roteador, verifique o log)"
    
    return JsonResponse({'success': True, 'message': msg, 'novo_status': device.status})

@login_required
@require_POST
def excluir_dispositivo(request, pk):
    device = get_object_or_404(Dispositivo, pk=pk)
    device.delete()
    # Atualiza o roteador para remover o bloqueio se existia
    aplicar_regras_firewall()
    return JsonResponse({'success': True})