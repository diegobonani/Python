import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from bs4 import BeautifulSoup
from estudos.models import Matricula, DiarioBordo, Disciplina

def puxar_boletim_publico_sed(aluno_perfil):
    # 1. Tratamento de Dados
    ra = str(aluno_perfil.ra_numero).strip()
    digito = str(aluno_perfil.ra_digito).strip().lower()
    uf = str(aluno_perfil.ra_uf).strip()
    nascimento = aluno_perfil.data_nascimento.strftime('%d%m%Y') if aluno_perfil.data_nascimento else ""

    print(f"\n--- INICIANDO {aluno_perfil.nome_completo} ---")

    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    try:
        # Abre o navegador
        driver = uc.Chrome(options=options, use_subprocess=True, version_main=144)
    except Exception as e:
        print(f"Erro ao abrir navegador: {e}")
        return False, "Falha no Chrome."

    wait = WebDriverWait(driver, 30)

    try:
        # Tenta ir direto na URL que você indicou
        url_boletim = "https://sed.educacao.sp.gov.br/Boletim/BoletimEscolar"
        driver.get(url_boletim)
        time.sleep(3) # Espera carregar/redirecionar

        # --- SEGURANÇA: Se o site jogar para a Home, o robô corrige ---
        if "boletim" not in driver.current_url.lower():
            print(">>> Site redirecionou para a Home. Buscando botão 'Boletim'...")
            try:
                # Clica no botão se necessário
                botao_boletim = wait.until(EC.element_to_be_clickable((
                    By.XPATH, "//a[contains(@href, 'Boletim') or contains(text(), 'Boletim')]"
                )))
                botao_boletim.click()
                time.sleep(3)
            except:
                print(">>> [ATENÇÃO] Não achei o botão automaticamente. Navegue manualmente se necessário.")

        # 2. Preenchimento
        print(">>> Aguardando formulário de RA...")
        # Espera o campo RA aparecer de verdade
        campo_ra = wait.until(EC.presence_of_element_located((By.ID, "NumeroRa")))
        
        print(">>> Preenchendo dados...")
        campo_ra.click()
        campo_ra.clear()
        campo_ra.send_keys(ra)
        
        driver.find_element(By.ID, "DigitoRa").send_keys(digito)
        driver.find_element(By.ID, "UfRa").send_keys(uf)
        
        campo_nasc = driver.find_element(By.ID, "DataNascimento")
        campo_nasc.click()
        campo_nasc.clear()
        time.sleep(0.5)
        campo_nasc.send_keys(nascimento)

        # 3. Espera Infinita pelo Captcha
        print(">>> [AÇÃO] Digite o Captcha e clique em PESQUISAR.")
        
        while True:
            # Verifica se a tabela apareceu
            if driver.find_elements(By.ID, "tabelaBoletim"):
                print(">>> [DETECTADO] Tabela encontrada! Extraindo dados...")
                break 
            
            # Verifica erro de dados
            if "Aluno não encontrado" in driver.page_source:
                print(">>> [ERRO SITE] Aluno não encontrado. Verifique os dados.")
                time.sleep(5)
                return False, "Dados incorretos."

            # Verifica janela fechada
            try:
                driver.title
            except:
                return False, "Janela fechada manualmente."
                
            time.sleep(1)

        # 4. Extração
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Pega os anos disponíveis
        try:
            select_ano = Select(driver.find_element(By.ID, "AnoLetivo"))
            anos = []
            for opt in select_ano.options:
                texto = opt.text.strip()
                # Pega apenas os 4 primeiros dígitos (o ano)
                if len(texto) >= 4 and texto[:4].isdigit():
                    anos.append(texto)
        except:
            anos = ["Atual"]

        total_salvo = 0
        if "Atual" in anos:
             tabela = soup.find('table', {'id': 'tabelaBoletim'})
             total_salvo += processar_tabela_sed(aluno_perfil, 2026, tabela)
        else:
            for ano in anos:
                print(f" -> Baixando ano {ano}...")
                select_ano.select_by_visible_text(ano)
                driver.find_element(By.ID, "btnPesquisar").click()
                time.sleep(4)
                
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                tabela = soup.find('table', {'id': 'tabelaBoletim'})
                if tabela:
                    # Usa int(ano[:4]) para pegar só "2025" de "2025 - Anual"
                    qtd = processar_tabela_sed(aluno_perfil, int(ano[:4]), tabela)
                    total_salvo += qtd

        print(f">>> FINALIZADO! {total_salvo} notas salvas.")
        return True, f"Sucesso! {total_salvo} notas."

    except Exception as e:
        print(f"\n>>> ERRO TÉCNICO: {str(e)}")
        return False, f"Erro: {str(e)}"
    
    finally:
        if 'driver' in locals():
            print("\n" + "="*40)
            print(" Pressione [ENTER] para fechar o navegador.")
            print("="*40 + "\n")
            try:
                input()
                driver.quit()
            except:
                pass

def processar_tabela_sed(perfil, ano, tabela_html):
    rows = tabela_html.find_all('tr')
    if not rows: return 0

    matricula, _ = Matricula.objects.get_or_create(
        aluno=perfil, 
        ano_letivo=ano,
        defaults={'ano_serie_atual': 0, 'nivel_atual': 'F1'} 
    )

    count = 0
    for row in rows:
        cols = row.find_all('td')
        if len(cols) >= 5: 
            nome = cols[0].text.strip()
            
            if not nome or any(x in nome for x in ["Componente", "Legenda", "Frequência", "Total"]): 
                continue

            # CRIAÇÃO DA DISCIPLINA VINCULADA AO ALUNO
            disc, created = Disciplina.objects.get_or_create(
                nome=nome, 
                usuario=perfil.usuario, # VÍNCULO CORRETO
                defaults={'categoria': 'ESCOLA'}
            )
            
            if created:
                print(f"    -> [NOVA] Disciplina criada: {nome}")

            def safe_float(val):
                if not val: return None
                v = val.strip().replace(',', '.')
                if not v or v == '-' or not v[0].isdigit(): return None
                try: return float(v)
                except: return None
            
            try:
                n1 = safe_float(cols[1].text)
                n2 = safe_float(cols[2].text)
                n3 = safe_float(cols[3].text)
                n4 = safe_float(cols[4].text)
                
                faltas = 0
                if len(cols) > 5:
                    f_val = safe_float(cols[5].text)
                    if f_val: faltas = int(f_val)
                
                DiarioBordo.objects.update_or_create(
                    matricula=matricula, 
                    disciplina_base=disc,
                    defaults={
                        'nota_1_bim': n1, 'nota_2_bim': n2,
                        'nota_3_bim': n3, 'nota_4_bim': n4,
                        'total_faltas': faltas
                    }
                )
                count += 1
            except Exception as e:
                continue

    return count