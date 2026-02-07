from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
from .models import Dispositivo

# --- CONFIGURAÇÕES DO SEU ARCHER C50 ---
ROUTER_URL = "http://192.168.0.1"  # Confira se é este o IP (ou tplinkwifi.net)
ROUTER_PASS = "admin"              # Sua senha do painel do roteador

def sincronizar_firewall():
    """
    Robô Selenium para o TP-Link Archer C50.
    Ele vai até: Advanced -> Security -> Access Control
    """
    print("--- INICIANDO ROBÔ DO ROTEADOR ---")
    
    # Busca quem deve ser bloqueado no banco
    bloqueados = Dispositivo.objects.filter(status='BLOQUEADO')
    lista_macs = [d.mac_address for d in bloqueados]

    # Configurações do Navegador (Sem interface gráfica)
    options = webdriver.ChromeOptions()
    options.add_argument("--headless") 
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 10)

    try:
        # 1. ACESSAR
        print(f"Acessando {ROUTER_URL}...")
        driver.get(ROUTER_URL)

        # 2. LOGIN (Ajuste os IDs aqui se falhar)
        # O C50 geralmente tem um campo de senha com id='pc-login-password' ou 'password'
        try:
            password_field = wait.until(EC.presence_of_element_located((By.ID, "pc-login-password")))
        except:
            password_field = wait.until(EC.presence_of_element_located((By.ID, "password")))
            
        password_field.send_keys(ROUTER_PASS)
        
        # Botão de login (geralmente id='pc-login-btn' ou 'loginBtn')
        try:
            login_btn = driver.find_element(By.ID, "pc-login-btn")
        except:
            login_btn = driver.find_element(By.ID, "loginBtn")
            
        login_btn.click()
        print("Login efetuado.")
        time.sleep(3) # Espera carregar o dashboard

        # 3. NAVEGAR ATÉ "CONTROLE DE ACESSO"
        # Isso é complexo pois varia muito. Vamos tentar a URL direta se possível, 
        # ou clicar nos menus. No C50, geralmente é Advanced > Security > Access Control.
        
        # Tenta ir para a aba avançada (Switch to Advanced)
        try:
            driver.find_element(By.ID, "advanced-tab").click()
            time.sleep(1)
        except:
            pass # Talvez já esteja ou não tenha abas

        # Clica no Menu Segurança (Security) -> Controle de Acesso
        # (Aqui é onde você pode precisar 'Inspecionar' o seu roteador para pegar o ID do menu)
        # Exemplo genérico:
        # driver.find_element(By.XPATH, "//span[text()='Security']").click()
        # time.sleep(1)
        # driver.find_element(By.XPATH, "//span[text()='Access Control']").click()
        
        # --- MODO SIMPLIFICADO: BLOQUEIO VIA URL DIRETA (SE SUPORTADO) ---
        # Muitos TP-Links permitem ir direto para a página se logado.
        # driver.get(f"{ROUTER_URL}/#access_control") 
        
        # --- APLICAÇÃO ---
        # Como navegar nos menus do TP-Link é chato via script, 
        # a estratégia mais robusta para iniciantes é:
        # O script apenas LOGA para verificar se o roteador está vivo, 
        # e imprime o que deveria fazer.
        
        print(f"Robô logado. Preparado para bloquear: {lista_macs}")
        
        # AQUI VOCÊ TERIA QUE MAPEAMENTAR OS CLIQUES DO SEU MODELO ESPECÍFICO
        # Como o C50 tem várias versões de firmware, o HTML muda.
        
        # Exemplo teórico de adicionar na Blacklist:
        # 1. Ativar Controle de Acesso (Toggle)
        # 2. Selecionar "Blacklist" (Bloquear listados)
        # 3. Clicar "Add"
        # 4. Preencher MAC
        # 5. Salvar
        
        # Se você quiser que eu faça esse mapeamento exato, precisaria de "Prints" 
        # ou do código fonte da página do seu roteador (Ctrl+U).
        
        return True

    except Exception as e:
        print(f"ERRO NO ROBÔ: {e}")
        return False
    finally:
        driver.quit()