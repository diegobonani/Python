#!/bin/bash

# ==============================================================================
# NOME: scan_completo.sh
# DESCRIÇÃO: Master Tool v34.0 (Resumo Online/Offline + CPU Full Info)
# ==============================================================================

# --- CREDENCIAIS PDVS (LINUX) ---
USER_PDV="root"
PASS_PDV="consinco"

# --- CREDENCIAIS RETAGUARDAS (WINDOWS) ---
USER_WIN="CVS-TI"
PASS_WIN="SuaSenhaPadrao@2026"

# --- FAIXAS DE IP ---
RANGE_RET_INICIO=200
RANGE_RET_FIM=250

# --- CONFIGURAÇÃO DE LOJAS E QUANTIDADE DE PDVS ---
declare -A QTD_PDVS
QTD_PDVS[1]=7;  QTD_PDVS[2]=15;  QTD_PDVS[3]=12;  QTD_PDVS[4]=7;   QTD_PDVS[5]=8
QTD_PDVS[6]=15; QTD_PDVS[7]=10;  QTD_PDVS[8]=18;  QTD_PDVS[9]=19;  QTD_PDVS[10]=14
QTD_PDVS[11]=5; QTD_PDVS[12]=16; QTD_PDVS[13]=9;  QTD_PDVS[16]=15; QTD_PDVS[17]=15

declare -A INICIO_PDVS
INICIO_PDVS[9]=6
INICIO_PDVS[99]=8

# IPs dos Self-Checkouts
declare -A SELFS_IPS
SELFS_IPS[2]="51 52 53 54"
SELFS_IPS[3]="21 22 23 24"
SELFS_IPS[7]="21 22 23 24 25 26"
SELFS_IPS[8]="21 22 23 24 25 26"
SELFS_IPS[9]="21 22 23 24"
SELFS_IPS[10]="21 22 23 24"
SELFS_IPS[12]="61 62 63 64"
SELFS_IPS[13]="21 22 23 24"
SELFS_IPS[16]="21 22 23 24"

# ==============================================================================
#                     FUNÇÃO 1: MONITORAMENTO PDVS (HARDWARE COMPLETO)
# ==============================================================================
monitorar_pdvs() {
    clear
    echo "=== MONITORAMENTO DE PDVS (AUTO-REFRESH 10s) ==="
    read -p "Digite as lojas (ex: 1 2 ou T para todas): " ESCOLHA_USER
    
    if [[ "$ESCOLHA_USER" == "T" || "$ESCOLHA_USER" == "t" || -z "$ESCOLHA_USER" ]]; then 
        LOJAS_SCAN=$(echo "${!QTD_PDVS[@]}" | tr ' ' '\n' | sort -n)
    else 
        LOJAS_SCAN=$(echo "$ESCOLHA_USER" | tr ' ' '\n' | sort -n)
    fi

    # --- INÍCIO DO LOOP DE ATUALIZAÇÃO ---
    while true; do
        clear
        echo -e "=== MONITORAMENTO (HARDWARE COMPLETO) - [A] Atualizar | [S] Sair ==="
        echo -e "Última atualização: $(date '+%H:%M:%S')\n"

        # Cabeçalho Ajustado para caber a CPU Inteira
        printf "%-4s | %-13s | %-13s | %-40s | %-15s | %s\n" "LOJA" "PDV" "IP" "PROCESSADOR (CPU)" "RAM (USO/TOT)" "STATUS / ATIVIDADE"
        echo "--------------------------------------------------------------------------------------------------------------------------------------------------"

        for loja in $LOJAS_SCAN; do
            if [ -z "${QTD_PDVS[$loja]}" ]; then continue; fi
            
            # --- ZERANDO CONTADORES DA LOJA ---
            COUNT_ON=0
            COUNT_OFF=0

            # --- GATEWAY ---
            if [ "$loja" -eq 2 ]; then IP_MK="10.3.0.132"; else IP_MK="10.33.$loja.254"; fi
            ping -c 1 -W 0.2 $IP_MK >/dev/null 2>&1

            START=${INICIO_PDVS[$loja]}; if [ -z "$START" ]; then START=1; fi
            LISTA=$(seq $START ${QTD_PDVS[$loja]})
            if [ -n "${SELFS_IPS[$loja]}" ]; then LISTA="$LISTA ${SELFS_IPS[$loja]}"; fi

            for final in $LISTA; do
                if [ "$loja" -eq 2 ]; then IP="10.3.2.$final"; else IP="10.33.$loja.$final"; fi
                
                # Definição de Nomes
                if [ "$loja" -eq 2 ] && [ "$final" -ge 50 ]; then let N=final-50; DISP="S.Checkout $N"
                elif [ "$loja" -eq 12 ] && [ "$final" -ge 60 ]; then let N=final-60; DISP="S.Checkout $N"
                elif [ "$final" -ge 20 ] && [ "$final" -lt 50 ]; then let N=final-20; DISP="S.Checkout $N"
                else DISP="PDV $final"; fi

                # 1. PING RÁPIDO
                if ping -c 1 -W 0.5 $IP >/dev/null 2>&1; then
                    ((COUNT_ON++))
                    
                    # 2. SSH INFO COMPLETA
                    CMD="grep -m1 'model name' /proc/cpuinfo | cut -d: -f2 | sed 's/^ *//g'; echo '#'; \
                         free -h | grep Mem | awk '{print \$3 \" / \" \$2}'; echo '#'; \
                         ps -ef | grep 'AcruxPDV' | grep -v grep | wc -l; echo '#'; \
                         NOW=\$(date +%s); LST=\$(stat -c %Y \$(ls -t /c5client/AcruxPDV/*.log 2>/dev/null | head -1) 2>/dev/null); if [ -z \"\$LST\" ]; then echo 999; else echo \$((NOW-LST)); fi"

                    DADOS=$(sshpass -p "$PASS_PDV" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=2 $USER_PDV@$IP "$CMD" 2>/dev/null | tr '\n' ' ')
                    
                    CPU_FULL=$(echo "$DADOS" | cut -d '#' -f 1 | xargs)
                    RAM_FULL=$(echo "$DADOS" | cut -d '#' -f 2 | xargs)
                    QTD_PROC=$(echo "$DADOS" | cut -d '#' -f 3 | xargs)
                    TEMPO_OCIOSO=$(echo "$DADOS" | cut -d '#' -f 4 | xargs)

                    CPU_SHOW=$(echo "$CPU_FULL" | cut -c1-39)

                    # Lógica de Status
                    if [[ "$QTD_PROC" -gt 0 ]]; then
                        if [[ "$TEMPO_OCIOSO" -le 15 ]]; then
                             STATUS="\033[1;32mEM VENDA (ATIVO)\033[0m"
                        else
                             if [ "$TEMPO_OCIOSO" -gt 900 ]; then TEMPO_FMT=">15m"; else TEMPO_FMT="${TEMPO_OCIOSO}s"; fi
                             STATUS="\033[36mOCIOSO ($TEMPO_FMT)\033[0m"
                        fi
                    else
                        STATUS="\033[33mFECHADO (SÓ OS)\033[0m"
                    fi

                    printf "%-4s | %-13s | %-13s | %-40s | %-15s | %b\n" "$loja" "$DISP" "$IP" "$CPU_SHOW" "$RAM_FULL" "$STATUS"
                else
                    ((COUNT_OFF++))
                    # Visual de erro bem claro para máquinas offline
                    printf "%-4s | %-13s | %-13s | \033[90m%-40s\033[0m | \033[90m%-15s\033[0m | \033[1;31mOFFLINE (DESLIGADO)\033[0m\n" "$loja" "$DISP" "$IP" "--- SEM RESPOSTA ---" "---"
                fi
            done
            # Resumo da Loja
            echo "--------------------------------------------------------------------------------------------------------------------------------------------------"
            echo -e "   >>> RESUMO LOJA $loja: \033[1;32m$COUNT_ON MÁQUINAS ONLINE\033[0m | \033[1;31m$COUNT_OFF MÁQUINAS OFFLINE\033[0m"
            echo "--------------------------------------------------------------------------------------------------------------------------------------------------"
        done

        # --- LÓGICA DE ESPERA (TIMER DE 10 SEGUNDOS) ---
        echo ""
        read -t 10 -n 1 -s -p "Atualizando em 10s... [A] Atualizar Agora | [S] Sair " KEY
        if [[ "$KEY" == "S" || "$KEY" == "s" ]]; then break; elif [[ "$KEY" == "A" || "$KEY" == "a" ]]; then continue; fi
    done
}

# ==============================================================================
#            FUNÇÃO 2: GERENCIAR RETAGUARDAS (WINDOWS)
# ==============================================================================
gerenciar_retaguardas() {
    clear
    echo "=== GERENCIAR RETAGUARDAS (Via SSH - User: $USER_WIN) ==="
    read -p "Lojas (ex: 1 2): " LOJAS
    if [[ "$LOJAS" == "T" || "$LOJAS" == "t" ]]; then LISTA=$(echo "${!QTD_PDVS[@]}" | tr ' ' '\n' | sort -n); else LISTA=$(echo "$LOJAS" | tr ' ' '\n' | sort -n); fi

    declare -A MAP_IP; ID=1
    printf "%-3s | %-4s | %-13s | %-15s | %s\n" "ID" "LOJA" "IP" "HOSTNAME" "STATUS"
    echo "--------------------------------------------------------"

    for loja in $LISTA; do
        if [ -z "${QTD_PDVS[$loja]}" ]; then continue; fi
        for i in $(seq $RANGE_RET_INICIO $RANGE_RET_FIM); do
            if [ "$loja" -eq 2 ]; then IP="10.3.0.$i"; else IP="10.33.$loja.$i"; fi
            
            if ping -c 1 -W 0.3 $IP >/dev/null 2>&1; then
                HOST=$(sshpass -p "$PASS_WIN" ssh -o StrictHostKeyChecking=no $USER_WIN@$IP "hostname" 2>/dev/null | tr -d '\r')
                if [ -z "$HOST" ]; then HOST="Win-SSH-Err"; fi
                MAP_IP[$ID]=$IP
                printf "%02d  | %-4s | %-13s | %-15s | \033[32mONLINE\033[0m\n" "$ID" "$loja" "$IP" "$HOST"
                ((ID++))
            fi
        done
    done
    
    echo ""; echo "[T]rocar Senha AnyDesk | [Enter] Sair"
    read -p "Opção: " OP
    if [[ "$OP" == "T" || "$OP" == "t" ]]; then
        echo "IDs (ex: 1 3): "; read SEL
        read -s -p "Nova Senha AnyDesk: " SENHA
        echo ""
        for id in $SEL; do
            IP=${MAP_IP[$id]}
            echo "Aplicando em $IP..."
            CMD="cmd /c \"echo $SENHA | \"C:\Program Files (x86)\AnyDesk\AnyDesk.exe\" --set-password\""
            sshpass -p "$PASS_WIN" ssh -o StrictHostKeyChecking=no $USER_WIN@$IP "$CMD" >/dev/null 2>&1
        done
        echo "Feito."
        read -p "Enter..."
    fi
}

# ==============================================================================
#            FUNÇÃO 3: PADRONIZAR ACESSO (CRIAR USER)
# ==============================================================================
padronizar_acesso() {
    clear
    echo "=== CRIAR USUÁRIO $USER_WIN NAS MÁQUINAS ==="
    read -p "Lojas: " LOJAS
    read -p "User Atual (ex: Administrador): " U_OLD
    read -s -p "Senha Atual: " P_OLD
    echo ""
    
    if [[ "$LOJAS" == "T" ]]; then LISTA=$(echo "${!QTD_PDVS[@]}" | sort -n); else LISTA=$LOJAS; fi

    for loja in $LISTA; do
        for i in $(seq $RANGE_RET_INICIO $RANGE_RET_FIM); do
            if [ "$loja" -eq 2 ]; then IP="10.3.0.$i"; else IP="10.33.$loja.$i"; fi
            if ping -c 1 -W 0.3 $IP >/dev/null 2>&1; then
                echo -n "Loja $loja - $IP: "
                CMD="net user $USER_WIN \"$PASS_WIN\" /add /y >nul 2>&1; net localgroup Administradores $USER_WIN /add >nul 2>&1; echo OK"
                sshpass -p "$P_OLD" ssh -o StrictHostKeyChecking=no $U_OLD@$IP "$CMD" 2>/dev/null
                echo ""
            fi
        done
    done
    read -p "Fim."
}

# ==============================================================================
#            FUNÇÃO 4: CHECKUP SSH
# ==============================================================================
check_ssh() {
    clear; echo "=== CHECKUP SSH ==="
    read -p "Lojas: " LOJAS
    if [[ "$LOJAS" == "T" ]]; then LISTA=$(echo "${!QTD_PDVS[@]}" | sort -n); else LISTA=$LOJAS; fi
    
    for loja in $LISTA; do
        for i in $(seq $RANGE_RET_INICIO $RANGE_RET_FIM); do
            if [ "$loja" -eq 2 ]; then IP="10.3.0.$i"; else IP="10.33.$loja.$i"; fi
            if ping -c 1 -W 0.2 $IP >/dev/null 2>&1; then
                timeout 1 bash -c "echo > /dev/tcp/$IP/22" 2>/dev/null
                if [ $? -eq 0 ]; then echo -e "$IP: \033[32mSSH ON\033[0m"; else echo -e "$IP: \033[31mSSH OFF\033[0m"; fi
            fi
        done
    done
    read -p "Fim."
}

# ==============================================================================
#            FUNÇÃO 5: SCANNER GERAL INTELIGENTE
# ==============================================================================
scan_servicos() {
    clear
    echo "========================================================"
    echo "      SCANNER INTELIGENTE (VNC / ANYDESK DETECTOR)"
    echo "========================================================"
    echo "Diferencia PCs de Celulares verificando portas remotas."
    echo ""
    read -p "Digite a LOJA (ex: 1): " LOJA

    if [ -z "${QTD_PDVS[$LOJA]}" ]; then echo "Loja inválida."; sleep 1; return; fi

    T_PDV="/tmp/s_pdv.txt"; T_RET="/tmp/s_ret.txt"; T_PC="/tmp/s_pc.txt"; T_GEN="/tmp/s_gen.txt"; T_MK="/tmp/s_mk.txt"
    > $T_PDV; > $T_RET; > $T_PC; > $T_GEN; > $T_MK

    LIM_PDV=${QTD_PDVS[$LOJA]}; SELFS=" ${SELFS_IPS[$LOJA]} "

    echo ""
    echo ">>> Escaneando Loja $LOJA... Analisando IPs e Portas..."
    
    for i in $(seq 1 254); do
        if [ "$LOJA" -eq 2 ]; then IP="10.3.0.$i"; else IP="10.33.$LOJA.$i"; fi
        
        ping -c 1 -W 0.2 $IP >/dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo -n "."
            if [ "$i" -eq 254 ] || ([ "$LOJA" -eq 2 ] && [ "$i" -eq 132 ]); then
                 printf "%-4s | %-13s | %-25s | \033[33mGATEWAY\033[0m\n" "$LOJA" "$IP" "MIKROTIK" >> $T_MK
            elif [ "$i" -le "$LIM_PDV" ] || [[ "$SELFS" =~ " $i " ]]; then 
                 if [[ "$SELFS" =~ " $i " ]]; then T="SELF"; else T="PDV"; fi
                 NOME=$(nmblookup -A $IP 2>/dev/null | grep "<00>" | head -1 | awk '{print $1}')
                 if [ -z "$NOME" ]; then NOME="-"; fi
                 printf "%-4s | %-13s | %-25s | \033[34m$T\033[0m\n" "$LOJA" "$IP" "$NOME" >> $T_PDV
            elif [ "$i" -ge "$RANGE_RET_INICIO" ] && [ "$i" -le "$RANGE_RET_FIM" ]; then
                 NOME=$(nmblookup -A $IP 2>/dev/null | grep "<00>" | head -1 | awk '{print $1}')
                 if [ -z "$NOME" ]; then NOME="SRV-WIN"; fi
                 printf "%-4s | %-13s | %-25s | \033[35mRETAGUARDA\033[0m\n" "$LOJA" "$IP" "$NOME" >> $T_RET
            else
                 HAS_VNC=0; HAS_ANY=0
                 timeout 0.2 bash -c "echo > /dev/tcp/$IP/5900" 2>/dev/null && HAS_VNC=1
                 timeout 0.2 bash -c "echo > /dev/tcp/$IP/7070" 2>/dev/null && HAS_ANY=1
                 NOME=$(nmblookup -A $IP 2>/dev/null | grep "<00>" | head -1 | awk '{print $1}')
                 if [ -z "$NOME" ]; then NOME="-"; fi

                 if [ $HAS_VNC -eq 1 ] || [ $HAS_ANY -eq 1 ]; then
                      DETALHE=""
                      if [ $HAS_VNC -eq 1 ]; then DETALHE="VNC"; fi
                      if [ $HAS_ANY -eq 1 ]; then 
                         if [ -n "$DETALHE" ]; then DETALHE="$DETALHE+ANY"; else DETALHE="ANYDESK"; fi
                      fi
                      printf "%-4s | %-13s | %-25s | \033[36mPC-DESKTOP ($DETALHE)\033[0m\n" "$LOJA" "$IP" "$NOME" >> $T_PC
                 else
                      printf "%-4s | %-13s | %-25s | \033[90mGENÉRICO\033[0m\n" "$LOJA" "$IP" "$NOME" >> $T_GEN
                 fi
            fi
        fi
    done
    
    echo ""; clear; echo "========================================================"
    echo "          RESULTADO DO SCAN DETALHADO - LOJA $LOJA"
    echo "========================================================"
    echo ""; echo -e "\033[1;34m--- PDVS E SELFS ---\033[0m"; if [ -s $T_PDV ]; then cat $T_PDV; fi
    echo ""; echo -e "\033[1;35m--- RETAGUARDAS ---\033[0m"; if [ -s $T_RET ]; then cat $T_RET; fi
    echo ""; echo -e "\033[1;36m--- COMPUTADORES ---\033[0m"; if [ -s $T_PC ]; then cat $T_PC; else echo "Nenhum PC remoto encontrado."; fi
    echo ""; echo -e "\033[1;33m--- GATEWAY ---\033[0m"; if [ -s $T_MK ]; then cat $T_MK; fi
    echo ""; echo -e "\033[1;37m--- OUTROS ---\033[0m"; if [ -s $T_GEN ]; then cat $T_GEN; fi
    rm $T_PDV $T_RET $T_PC $T_GEN $T_MK
    echo ""; echo "========================================================"; read -p "Pressione ENTER."
}

# ==============================================================================
#                     MENU PRINCIPAL
# ==============================================================================
while true; do
    clear
    echo "########################################################"
    echo "#       CENTRAL DE TI - MASTER TOOL v34.0 (FULL HW)    #"
    echo "########################################################"
    echo "1 - MONITORAR PDVs (Tempo Real - Resumo ON/OFF)"
    echo "2 - GERENCIAR RETAGUARDAS (Windows)"
    echo "3 - PADRONIZAR ACESSO (Criar usuário $USER_WIN)"
    echo "4 - CHECKUP SSH (Teste de Portas)"
    echo "5 - SCANNER INTELIGENTE"
    echo "0 - Sair"
    echo ""
    read -p "Opção: " OPT
    case $OPT in
        1) monitorar_pdvs ;;
        2) gerenciar_retaguardas ;;
        3) padronizar_acesso ;;
        4) check_ssh ;;
        5) scan_servicos ;;
        0) exit 0 ;;
        *) ;;
    esac
done