import routeros_api
import time
import sys

# --- CONFIGURAÇÕES ---
HOST = '10.3.0.132'
USER = 'diego.bonani'
PASSWORD = 'Senha@123'
INTERFACE = 'ether3-LAN'  # Nome EXATO da interface

# Critérios para considerar "SUSPEITO"
LIMIT_PPS = 1000  # Se passar de 1000 pacotes/s, entra no radar
LIMIT_MBPS = 10   # Se passar de 10 Mbps em uma única conexão, entra no radar

def parse_val(value_str):
    """Converte strings do Mikrotik (10.5Mbps, 500kbps) para números inteiros."""
    if not value_str: return 0
    s = str(value_str).lower().replace('bps', '')
    try:
        if 'g' in s: return float(s.replace('g', '')) * 1000000000
        if 'm' in s: return float(s.replace('m', '')) * 1000000
        if 'k' in s: return float(s.replace('k', '')) * 1000
        return float(s)
    except:
        return 0

def main():
    print(f"\n--- INICIANDO AUDITORIA NO MIKROTIK {HOST} ---")
    print(f"--- Interface Alvo: {INTERFACE} ---")
    
    try:
        connection = routeros_api.RouterOsApiPool(HOST, username=USER, password=PASSWORD, plaintext_login=True)
        api = connection.get_api()
    except Exception as e:
        print(f"ERRO DE CONEXÃO: {e}")
        sys.exit(1)

    try:
        while True:
            print("\n" + "="*80)
            print(f"ETAPA 1: Verificando Tabela ARP (Procurando Duplicidade de IP)...")
            
            arp_list = api.get_resource('/ip/arp').get()
            
            # Dicionário para rastrear duplicidade: { '192.168.1.10': ['MAC1', 'MAC2'] }
            ip_tracker = {}
            suspects_arp = []

            for entry in arp_list:
                ip = entry.get('address')
                mac = entry.get('mac-address')
                if ip and mac:
                    if ip not in ip_tracker:
                        ip_tracker[ip] = []
                    
                    # Se o MAC ainda não está na lista desse IP, adiciona
                    if mac not in ip_tracker[ip]:
                        ip_tracker[ip].append(mac)

            # Filtra quem tem mais de 1 MAC
            for ip, macs in ip_tracker.items():
                if len(macs) > 1:
                    suspects_arp.append({'ip': ip, 'macs': macs, 'reason': 'CONFLITO: IP em múltiplos MACs'})

            print(f"ETAPA 2: Analisando Tráfego em Tempo Real (Aguarde 5 segundos)...")
            
            # Executa o Torch por 5 segundos
            try:
                torch_res = api.get_resource('/tool/torch').call('monitor', {
                    'interface': INTERFACE,
                    'duration': '5',
                    'src-address': '0.0.0.0/0',
                    'dst-address': '0.0.0.0/0',
                    'port': 'any',
                    'protocol': 'any'
                })
            except Exception as e:
                print(f"Erro no Torch: {e}")
                torch_res = []

            suspects_traffic = []

            if torch_res:
                # O torch retorna uma lista de dicionários dentro da primeira posição
                traffic_list = torch_res[0] if isinstance(torch_res, list) and len(torch_res) > 0 else []

                for t in traffic_list:
                    src = t.get('src-address', 'Desconhecido')
                    dst = t.get('dst-address', 'Desconhecido')
                    tx = t.get('tx-rate', '0')
                    rx = t.get('rx-rate', '0')
                    proto = t.get('ip-protocol', t.get('protocol', '??'))
                    
                    # Converte para números para analisar
                    tx_val = parse_val(tx)
                    rx_val = parse_val(rx)
                    
                    # Se for Broadcast
                    is_broadcast = '255.255.255.255' in dst
                    
                    # Se for tráfego muito alto
                    is_heavy = (tx_val + rx_val) > (LIMIT_MBPS * 1000000)

                    if is_broadcast or is_heavy:
                        # Tenta achar o MAC desse IP na tabela ARP que baixamos antes
                        mac_found = "MAC Não encontrado (Sem ARP)"
                        if src in ip_tracker and ip_tracker[src]:
                            mac_found = ip_tracker[src][0] # Pega o primeiro MAC conhecido

                        reason = []
                        if is_broadcast: reason.append("BROADCAST STORM")
                        if is_heavy: reason.append(f"ALTO TRÁFEGO (>{LIMIT_MBPS}Mbps)")

                        suspects_traffic.append({
                            'ip': src,
                            'dst': dst,
                            'mac': mac_found,
                            'tx': tx,
                            'rx': rx,
                            'reason': " + ".join(reason)
                        })

            # --- RELATÓRIO FINAL DA RODADA ---
            all_suspects = suspects_arp + suspects_traffic
            unique_ips = list(set([s['ip'] for s in all_suspects]))
            count = len(unique_ips)

            print("\n" + "*"*80)
            print(f"RESULTADO DA ANÁLISE: {count} DISPOSITIVO(S) SUSPEITO(S) ENCONTRADO(S)")
            print("*"*80)

            if count == 0:
                print("Nenhum comportamento anômalo grave detectado nesta rodada.")
            else:
                print(f"{'IP SUSPEITO':<16} | {'MAC ADDRESS':<18} | {'MOTIVO DO ALERTA':<35} | {'TX/RX ATUAL'}")
                print("-" * 90)
                
                # Exibir ARP Suspects
                for s in suspects_arp:
                    print(f"{s['ip']:<16} | {str(s['macs']):<18} | {s['reason']:<35} | -")
                
                # Exibir Traffic Suspects
                for s in suspects_traffic:
                    print(f"{s['ip']:<16} | {s['mac']:<18} | {s['reason']:<35} | TX:{s['tx']} RX:{s['rx']}")

            print("\n(Pressione Ctrl+C para encerrar ou aguarde a próxima varredura...)")
            # time.sleep(2)

    except KeyboardInterrupt:
        print("\nAuditoria encerrada.")
    finally:
        connection.disconnect()

if __name__ == "__main__":
    main()