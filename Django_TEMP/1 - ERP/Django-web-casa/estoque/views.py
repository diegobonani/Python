import datetime,calendar,json,re,time,os,subprocess
import undetected_chromedriver as uc 
from bs4 import BeautifulSoup
from decimal import Decimal

# Selenium Imports (Necessários para o modo Ninja)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Django Imports
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import F, Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.conf import settings

# App Imports
from core.decorators import admin_required 
from core.models import Pet, EstoqueCategoria, Unidade, Imovel, Comodo, Localizacao
from financas.models import Financa 

from .models import (
    CatalogoPessoal, Estoque, EstoqueLog, HistoricoEstoque, ItemCasa, ItemFaltante, 
    ItemPet, ItemUsuario, ListaCompra, ListaCompraProduto
)

from .forms import (
    CatalogoPessoalForm, EstoqueForm, ItemFaltanteForm, 
    LancarDespesaCompraForm, ListaCompraForm, ListaCompraProdutoForm,
    converter_para_float
)

# ===================================================================
# 0. HELPER FUNCTIONS (AUXILIARES & LOGS)
# ===================================================================

def limpar_valor(valor_str):
    """ 
    Converte strings como 'R$ 5,90', '5,90' ou 'Qtde.: 2' para float 5.90. 
    Remove textos extras e converte vírgula para ponto.
    """
    if not valor_str: return 0.0
    # Remove R$, textos comuns e espaços
    limpo = valor_str.replace('R$', '').replace('Qtde.:', '').replace('Vl. Unit.:', '').replace(' ', '').strip()
    # Remove pontos de milhar (1.000,00 -> 1000,00)
    if '.' in limpo and ',' in limpo:
        limpo = limpo.replace('.', '')
    # Troca vírgula decimal por ponto
    limpo = limpo.replace(',', '.')
    try:
        return float(limpo)
    except ValueError:
        return 0.0

def safe_decimal(val):
    """ Converte inputs de formulário para Decimal do banco de dados. """
    if not val: return Decimal('0.00')
    if isinstance(val, (int, float, Decimal)): return val
    s = str(val).replace('R$', '').replace(' ', '').strip()
    if ',' in s and '.' in s: s = s.replace('.', '').replace(',', '.')
    elif ',' in s: s = s.replace(',', '.')
    try: return Decimal(s)
    except: return Decimal('0.00')

def importar_nota_sp(entrada):
    """
    Leitor 'Modo Assistido V15' (Janela Única + Tempo Longo).
    Abre o navegador e fica esperando (até 2 min) o usuário resolver o Captcha.
    Assim que a tabela de itens aparece, ele captura e fecha.
    """
    entrada = entrada.strip().replace(" ", "")
    
    if re.match(r'^\d{44}$', entrada):
        url = f"https://www.nfce.fazenda.sp.gov.br/NFCeConsultaPublica/Paginas/ConsultaPublica.aspx?chave={entrada}"
    else:
        url = entrada

    # --- 1. LIMPEZA DE PROCESSOS (Evita erro de arquivo travado) ---
    try:
        subprocess.run("taskkill /F /IM chromedriver.exe /T", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        appdata = os.getenv('APPDATA')
        path_exe = os.path.join(appdata, 'undetected_chromedriver', 'undetected_chromedriver.exe')
        if os.path.exists(path_exe):
            try: os.remove(path_exe)
            except: pass
    except: pass

    driver = None
    html_content = ""
    
    try:
        # --- 2. CONFIGURAÇÃO VISUAL (PARA VOCÊ VER E RESOLVER) ---
        options = uc.ChromeOptions()
        options.add_argument("--start-maximized") # Abre tela cheia
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        # options.add_argument("--headless") # COMENTADO: Queremos ver a janela!
        
        # Inicia o Navegador (Versão 143 Fixa)
        driver = uc.Chrome(options=options, use_subprocess=True, version_main=143)
        
        # Define um tempo limite alto para o carregamento da página
        driver.set_page_load_timeout(120) 
        
        driver.get(url)

        # --- 3. A ESPERA DO HUMANO (O PULO DO GATO) ---
        # O script agora para nesta linha e fica vigiando a página por 2 minutos.
        # Enquanto você resolve o Captcha, ele espera.
        # Assim que a classe 'txtTit' (nome do produto) aparecer na tela, ele prossegue.
        try:
            WebDriverWait(driver, 120).until(
                EC.presence_of_element_located((By.CLASS_NAME, "txtTit"))
            )
            
            # Deu certo! Você resolveu e os itens apareceram.
            time.sleep(1) # Espera 1 segundinho pra garantir que carregou tudo
            html_content = driver.page_source
            
        except Exception:
            # Se passou 2 minutos e a tabela não apareceu
            return {'sucesso': False, 'erro': "Tempo esgotado (2 min). O Captcha não foi resolvido ou a nota não carregou."}

    except Exception as e:
        return {'sucesso': False, 'erro': f"Erro ao abrir navegador: {str(e)}"}
    finally:
        # Fecha a janela automaticamente assim que terminar (sucesso ou erro)
        if driver:
            try: driver.quit()
            except: pass

    # --- 4. EXTRAÇÃO DOS DADOS (REGEX) ---
    if not html_content:
        return {'sucesso': False, 'erro': "Nenhum conteúdo lido."}

    soup = BeautifulSoup(html_content, 'html.parser')
    produtos = []

    topo = soup.find('div', class_='txtTopo') or soup.find('div', id='u20')
    mercado = topo.get_text(strip=True) if topo else "Mercado Desconhecido"

    itens_titulos = soup.find_all('span', class_='txtTit')
    if not itens_titulos: itens_titulos = soup.find_all('span', class_='txtTit2')

    for tag_nome in itens_titulos:
        try:
            nome = tag_nome.get_text(strip=True)
            container = tag_nome.find_parent('tr') or tag_nome.find_parent('div', id=re.compile(r'Item')) or tag_nome.parent.parent
            texto_full = container.get_text(" ", strip=True)

            codigo = ""
            match_cod = re.search(r'(?:Cód|Código)\.?\s*:?\s*(\d+)', texto_full, re.IGNORECASE)
            if match_cod: codigo = match_cod.group(1)

            qtd = 1.0
            match_qtd = re.search(r'(?:Qtde|Qtd)\.?\s*:?\s*([\d,.]+)', texto_full, re.IGNORECASE)
            if match_qtd: qtd = limpar_valor(match_qtd.group(1))

            unidade = "UN"
            match_un = re.search(r'UN\s*:?\s*([A-Z]{2,})', texto_full, re.IGNORECASE)
            if match_un: unidade = match_un.group(1).strip()

            preco_unit = 0.0
            match_vl = re.search(r'Vl\.?\s*Unit\.?\s*:?\s*([\d,.]+)', texto_full, re.IGNORECASE)
            if match_vl: preco_unit = limpar_valor(match_vl.group(1))

            preco_total = 0.0
            valores = re.findall(r'([\d,]+\d{2})', texto_full)
            valores_float = [limpar_valor(v) for v in valores]
            candidatos = [v for v in valores_float if v >= preco_unit]
            if candidatos: preco_total = candidatos[-1]
            else: preco_total = qtd * preco_unit

            produtos.append({
                'nome': nome, 'codigo': codigo, 'quantidade': qtd,
                'unidade': unidade, 'preco_unitario': preco_unit, 'preco_total': preco_total
            })
        except: continue

    if not produtos:
        return {'sucesso': False, 'erro': "Nenhum item identificado. O layout da página mudou?"}

    return {'sucesso': True, 'mercado': mercado, 'itens': produtos}

def _log_estoque_change(usuario, acao, item_obj, qtd_antiga=0, qtd_nova=0):
    """ 
    Registra histórico nas DUAS tabelas e salva SNAPSHOT para casos de exclusão.
    """
    
    # 1. Identifica o HUB (Estoque) e o Detalhe
    estoque_hub = None
    item_real = item_obj

    if isinstance(item_obj, Estoque):
        estoque_hub = item_obj
        item_real = item_obj.get_detalhe
    elif hasattr(item_obj, 'estoque'):
        estoque_hub = item_obj.estoque

    # 2. Prepara os Textos (Snapshot)
    nome_texto = getattr(item_real, 'nome', 'Item Desconhecido')
    local_texto = "-"
    setor = "Geral"
    cat = "-"

    if hasattr(item_real, 'categoria') and item_real.categoria:
        cat = item_real.categoria.nome_categoria

    # Lógica para descobrir o nome do local (Donos/Cômodos)
    if isinstance(item_real, ItemCasa): 
        setor = "Casa"
        if item_real.comodo:
            nome_imovel = item_real.comodo.imovel.nome if item_real.comodo.imovel else ""
            local_texto = f"{nome_imovel} - {item_real.comodo.nome}"
    elif isinstance(item_real, ItemPet): 
        setor = "Pet"
        if item_real.pet:
            local_texto = f"Pet: {item_real.pet.nome_pet}"
    elif isinstance(item_real, ItemUsuario): 
        setor = "Usuário"
        if item_real.usuario:
            local_texto = f"User: {item_real.usuario.username}"

    # 3. Grava no Log Legado (Texto)
    EstoqueLog.objects.create(
        usuario=usuario, acao=acao, item_nome=nome_texto, item_setor=setor,
        item_dono=local_texto, item_categoria=cat, 
        quantidade_antiga=qtd_antiga, quantidade_nova=qtd_nova
    )

    # 4. Grava no Histórico Relacional (COM SNAPSHOT)
    if estoque_hub:
        qtd_mov = abs(qtd_nova - qtd_antiga) if qtd_nova is not None and qtd_antiga is not None else 0
        
        # Define a observação
        obs_final = f"{acao} via Sistema"
        if acao == 'EXCLUSAO':
            obs_final = "Item Excluído do Sistema permanentemente."

        HistoricoEstoque.objects.create(
            estoque=estoque_hub,
            usuario=usuario,
            tipo_movimento=acao,
            quantidade_movimentada=qtd_mov,
            saldo_anterior=qtd_antiga,
            saldo_atual=qtd_nova,
            observacao=obs_final,
            # AQUI ESTÁ O SEGREDO: Salvamos o texto fixo
            item_nome_snapshot=nome_texto,
            item_local_snapshot=local_texto
        )

# ===================================================================
# 1. ABA VISÃO GERAL / ESTOQUE FÍSICO (CRUD E TABELA)
# ===================================================================

@login_required
@require_POST
@admin_required
def dar_baixa_item(request, pk):
    """ Reduz a quantidade de um item no estoque. """
    estoque = get_object_or_404(Estoque, pk=pk)
    item_real = estoque.get_detalhe
    if not item_real: return JsonResponse({'success': False, 'message': 'Erro de integridade.'}, status=400)

    try: qtd_baixa = safe_decimal(request.POST.get('quantidade'))
    except: return JsonResponse({'success': False, 'message': 'Qtd inválida.'}, status=400)
    
    if qtd_baixa <= 0: return JsonResponse({'success': False, 'message': 'Positiva.'}, status=400)
    if qtd_baixa > item_real.quantidade: return JsonResponse({'success': False, 'message': 'Saldo insuficiente.'}, status=400)
    
    item_real.quantidade -= qtd_baixa
    item_real.save()
    _log_estoque_change(request.user, 'BAIXA', item_real, qtd_nova=item_real.quantidade)
    return JsonResponse({'success': True, 'message': 'Baixa efetuada!'})

@login_required
@require_POST
@admin_required
def deletar_estoque_item(request, pk):
    """ Remove um item do estoque permanentemente. """
    estoque = get_object_or_404(Estoque, pk=pk)
    item_real = estoque.get_detalhe
    qtd_antiga = item_real.quantidade if item_real else 0
    _log_estoque_change(request.user, 'EXCLUSAO', estoque, qtd_antiga=qtd_antiga, qtd_nova=0)
    estoque.delete() 
    return JsonResponse({'success': True, 'message': 'Excluído.'})

@login_required
@require_POST
@admin_required
def editar_estoque_item(request, pk):
    """ Edita as propriedades de um item existente. """
    estoque = get_object_or_404(Estoque, pk=pk)
    try:
        item_real = estoque.get_detalhe
        
        if item_real:
            qtd_antiga = item_real.quantidade
            
            # Atualização de campos comuns
            item_real.nome = request.POST.get('nome_item')
            item_real.quantidade = safe_decimal(request.POST.get('quantidade'))
            item_real.estoque_minimo = safe_decimal(request.POST.get('estoque_minimo'))
            item_real.estoque_ideal = safe_decimal(request.POST.get('estoque_ideal'))
            
            if request.POST.get('categoria'): item_real.categoria_id = request.POST.get('categoria')
            if hasattr(item_real, 'preco'): item_real.preco = safe_decimal(request.POST.get('preco_unitario'))
            if hasattr(item_real, 'unidade_id') and request.POST.get('unidade'): item_real.unidade_id = request.POST.get('unidade')
            
            if hasattr(item_real, 'validade'):
                val = request.POST.get('data_validade')
                item_real.validade = val if val else None

            if estoque.setor == 'CASA':
                # Nota: Não editamos o Imóvel aqui diretamente para evitar inconsistência
                if request.POST.get('comodo'): item_real.comodo_id = request.POST.get('comodo')
                if request.POST.get('localizacao'): item_real.localizacao_id = request.POST.get('localizacao')
            
            item_real.save() 
            _log_estoque_change(request.user, 'EDICAO', item_real, qtd_antiga=qtd_antiga, qtd_nova=item_real.quantidade)
            return JsonResponse({'success': True, 'message': 'Atualizado!'})
    except Exception as e:
        return JsonResponse({'success': False, 'errors': {'geral': [str(e)]}}, status=400)

@login_required
@admin_required 
def gerenciar_estoque(request):
    """ View Principal: Renderiza a página e processa criação de novos itens. """
    
    # --- POST: SALVAR NOVO ITEM NO ESTOQUE FÍSICO ---
    if request.method == 'POST':
        form = EstoqueForm(request.POST)
        form_type = request.POST.get('form_type') 
        
        if form.is_valid():
            try:
                d = form.cleaned_data
                # Converte e protege valores numéricos
                qtd = safe_decimal(d.get('quantidade'))
                preco = safe_decimal(d.get('preco_unitario'))
                est_min = safe_decimal(d.get('estoque_minimo'))
                est_ideal = safe_decimal(d.get('estoque_ideal'))
                
                filho = None

                # 1. CASA (Com proteção para campos opcionais)
                if form_type == 'casa':
                    # Proteção: Se não tiver cômodo/local, força None para evitar erro 1452
                    comodo_obj = d.get('comodo') or None
                    local_obj = d.get('localizacao') or None

                    filho = ItemCasa.objects.create(
                        nome=d['nome_item'], 
                        categoria=d['categoria'], 
                        unidade=d['unidade'],
                        comodo=comodo_obj, 
                        localizacao=local_obj,
                        quantidade=qtd, 
                        preco=preco, 
                        validade=d['data_validade'],
                        estoque_minimo=est_min, 
                        estoque_ideal=est_ideal
                    )
                    Estoque.objects.create(setor='CASA', item_casa=filho)

                # 2. PET
                elif form_type == 'pet':
                    pet_obj = get_object_or_404(Pet, pk=request.POST.get('pet_id'))
                    filho = ItemPet.objects.create(
                        nome=d['nome_item'], 
                        pet=pet_obj, 
                        categoria=d['categoria'],
                        unidade=d['unidade'], 
                        quantidade=qtd, 
                        preco=preco, 
                        validade=d['data_validade'],
                        estoque_minimo=est_min, 
                        estoque_ideal=est_ideal
                    )
                    Estoque.objects.create(setor='PET', item_pet=filho)

                # 3. USUARIO
                elif form_type == 'usuario':
                    user_obj = get_object_or_404(User, pk=request.POST.get('usuario_id'))
                    filho = ItemUsuario.objects.create(
                        nome=d['nome_item'], 
                        usuario=user_obj, 
                        categoria=d['categoria'],
                        quantidade=qtd,
                        estoque_minimo=est_min, 
                        estoque_ideal=est_ideal
                    )
                    Estoque.objects.create(setor='USUARIO', item_usuario=filho)

                # Log de criação
                _log_estoque_change(request.user, 'CRIACAO', locals()['filho'], qtd_antiga=0, qtd_nova=qtd)
                return JsonResponse({'success': True, 'message': 'Salvo com sucesso!'})
            
            except Exception as e:
                # Retorna o erro exato para o JS (ajuda a debugar se persistir)
                return JsonResponse({'success': False, 'errors': {'geral': [f"Erro no banco: {str(e)}"]}}, status=400)
        else:
            return JsonResponse({'success': False, 'errors': json.loads(form.errors.as_json())}, status=400)

    # --- GET: RENDERIZAÇÃO INICIAL ---
    today = timezone.localdate()
    filtro_data_estoque_default = request.GET.get('filtro_data_estoque', '') 
    filtro_mes = request.GET.get('filtro_mes_ano', today.strftime('%Y-%m'))
    
    try: y, m = map(int, filtro_mes.split('-'))
    except: y, m = today.year, today.month

    compras = ListaCompra.objects.filter(data_compra__year=y, data_compra__month=m).order_by('-data_compra')

    imoveis_ativos = Imovel.objects.filter(finalidade__in=['MORADIA', 'VERANEIO']).order_by('nome')
    imoveis_inativos = Imovel.objects.exclude(finalidade__in=['MORADIA', 'VERANEIO']).order_by('nome')

    context = {
        'form_estoque': EstoqueForm(), 
        'form_lista_compra': ListaCompraForm(),
        'form_lancar_despesa': LancarDespesaCompraForm(usuario=request.user),
        'listas_de_compra': compras,
        'todos_usuarios': User.objects.all(),
        'todos_pets': Pet.objects.all(),
        'valor_filtro_html_compras': filtro_mes,
        'filtro_data_estoque_default': filtro_data_estoque_default,
        'imoveis_ativos': imoveis_ativos,      
        'imoveis_inativos': imoveis_inativos, 
    }
    return render(request, 'estoque/gerenciar_estoque.html', context)

@login_required
@admin_required
def tabela_estoque_unificada_partial(request):
    # Captura parâmetros
    setor = request.GET.get('setor', 'TODOS')
    owner_id = request.GET.get('owner_id')
    imovel_id = request.GET.get('imovel_id') 
    data_filtro = request.GET.get('data_filtro') 
    template_sufixo = request.GET.get('template_sufixo', '_tabela_estoque_unificada.html') 

    print(f"DEBUG: Carregando Tabela | Setor: {setor} | Imóvel: {imovel_id}")

    # 1. BASE DA QUERY
    qs = Estoque.objects.select_related(
        'item_casa', 'item_casa__comodo', 'item_casa__localizacao', 
        'item_casa__comodo__imovel', 
        'item_pet', 'item_pet__pet',
        'item_usuario', 'item_usuario__usuario'
    )

    # 2. LÓGICA DE ORDENAÇÃO INTELIGENTE (O SEGREDO DA ORGANIZAÇÃO)
    # Primeiro agrupa por Imóvel, depois por Cômodo, depois por Nome do Item
    qs = qs.order_by(
        'item_casa__comodo__imovel__nome', # 1º Agrupa por Casa
        'item_casa__comodo__nome',         # 2º Agrupa por Cômodo
        'item_casa__nome'                  # 3º Alfabetico
    )

    # 3. LÓGICA DE FILTRO DE IMÓVEL
    if setor in ['CASA', 'TODOS']:
        
        # CASO A: Todos os Imóveis (Mostra tudo, mas organizado pelo order_by acima)
        if imovel_id == 'TODOS' or not imovel_id:
            # Opcional: Esconder itens de imóveis de aluguel/venda se quiser
            # qs = qs.exclude(item_casa__comodo__imovel__finalidade__in=['ALUGUEL'])
            pass 
            
        # CASO B: Imóvel Específico
        elif str(imovel_id).isdigit():
            qs = qs.filter(
                Q(item_casa__comodo__imovel_id=int(imovel_id)) | 
                Q(setor__in=['PET', 'USUARIO']) # Mantém itens globais
            )

    # 4. Filtros Secundários (Dropdown Específico)
    if setor != 'TODOS': 
        qs = qs.filter(setor=setor)
    
    if owner_id and str(owner_id).isdigit():
        if setor == 'USUARIO': qs = qs.filter(item_usuario__usuario_id=owner_id)
        elif setor == 'PET': qs = qs.filter(item_pet__pet_id=owner_id)
        
        # Se filtrar por cômodo específico, obedece
        elif setor == 'CASA': qs = qs.filter(item_casa__comodo_id=owner_id)

    # ---------------------------------------------------------
    # CORREÇÃO DEFINITIVA DO FILTRO DE DATA (INTERVALO)
    # ---------------------------------------------------------
    if data_filtro: 
        try:
            # 1. Pega Ano e Mês do input (ex: "2026-01")
            ano_str, mes_str = data_filtro.split('-')
            ano = int(ano_str)
            mes = int(mes_str)
            
            # 2. Define o Início do Mês (Dia 1, 00:00:00)
            data_inicio = datetime.datetime(ano, mes, 1, 0, 0, 0)
            
            # 3. Define o Início do PRÓXIMO Mês (para usar como limite)
            if mes == 12:
                data_fim = datetime.datetime(ano + 1, 1, 1, 0, 0, 0)
            else:
                data_fim = datetime.datetime(ano, mes + 1, 1, 0, 0, 0)
            
            # 4. Aplica o filtro: Maior/Igual ao início E Estritamente Menor que o próximo mês
            # Isso cobre dia 1, dia 17, dia 31, qualquer horário.
            qs = qs.filter(data_cadastro__gte=data_inicio, data_cadastro__lt=data_fim)
            
            print(f"DEBUG DATETIME: Buscando de {data_inicio} até {data_fim} -> Encontrados: {qs.count()}")
            
        except Exception as e:
            print(f"ERRO CRÍTICO DATA: {e}")
            pass

    return render(request, f'partials/{template_sufixo}', {'itens_estoque': qs})

@login_required
@admin_required
def get_item_json(request, pk):
    """ Retorna dados de um item para preencher o modal de edição. """
    qs = Estoque.objects.select_related(
        'item_casa', 'item_pet', 'item_usuario',
        'item_casa__categoria', 'item_casa__unidade', 'item_casa__comodo', 'item_casa__localizacao',
        'item_pet__categoria', 'item_pet__unidade', 'item_usuario__categoria'
    )
    estoque = get_object_or_404(qs, pk=pk)
    data = {'id': estoque.id, 'setor': estoque.setor}
    
    item = estoque.get_detalhe
    
    if estoque.setor == 'CASA' and item:
        data.update({'comodo_id': item.comodo_id, 'localizacao_id': item.localizacao_id})

    if item:
        data.update({
            'nome_item': item.nome, 
            'quantidade': item.quantidade, 
            'categoria_id': item.categoria_id, 
            'estoque_minimo': item.estoque_minimo, 
            'estoque_ideal': item.estoque_ideal
        })
        
        if hasattr(item, 'preco'): data['preco_unitario'] = item.preco
        if hasattr(item, 'unidade_id'): data['unidade_id'] = item.unidade_id
        if hasattr(item, 'validade') and item.validade: data['data_validade'] = item.validade.strftime('%Y-%m-%d')
        else: data['data_validade'] = ''

    return JsonResponse(data)

@login_required
@admin_required
def meu_estoque_view(request):
    return render(request, 'estoque/meu_estoque.html', {'meus_itens_estoque': Estoque.objects.filter(setor='USUARIO', usuario=request.user)})

# ===================================================================
# 2. ABA COMPRAS (LISTAS DE SUPERMERCADO & TRIAGEM)
# ===================================================================

@login_required
def ler_nota_ajax(request):
    url = request.GET.get('url')
    if not url: return JsonResponse({'success': False, 'erro': 'URL vazia.'})

    if ListaCompra.objects.filter(url_nota=url).exists():
        compra_existente = ListaCompra.objects.get(url_nota=url)
        return JsonResponse({
            'success': False, 
            'erro': f'Esta nota já foi importada em {compra_existente.data_compra.strftime("%d/%m/%Y")}.'
        })

    try:
        resultado = importar_nota_sp(url)
        if resultado['sucesso']:
            # Carrega dados para a triagem
            comodos = list(Comodo.objects.select_related('imovel').values('id', 'nome', 'imovel__nome').order_by('imovel__nome', 'nome'))
            # Formatando nome para exibir "Cozinha (Casa Antiga)"
            for c in comodos:
                if c['imovel__nome']: c['nome'] = f"{c['nome']} ({c['imovel__nome']})"
            
            pets = list(Pet.objects.values('id', 'nome_pet').order_by('nome_pet'))
            users = list(User.objects.values('id', 'username').order_by('username'))
            
            return JsonResponse({
                'success': True,
                'mercado': resultado['mercado'],
                'total_itens': len(resultado['itens']),
                'valor_total': sum(item['preco_total'] for item in resultado['itens']),
                'data_emissao': timezone.localdate().strftime('%Y-%m-%d'),
                'itens': resultado['itens'],
                'opcoes_destino': { 'comodos': comodos, 'pets': pets, 'usuarios': users }
            })
        else:
            return JsonResponse({'success': False, 'erro': resultado['erro']})
    except Exception as e:
        return JsonResponse({'success': False, 'erro': f"Erro interno: {str(e)}"})

@login_required
def registrar_compra_ajax(request):
    if request.method == 'POST':
        form = ListaCompraForm(request.POST)
        itens_triagem_json = request.POST.get('itens_triagem_json')
        url_nota_recebida = request.POST.get('url_nota', '').strip()

        if form.is_valid():
            if url_nota_recebida and ListaCompra.objects.filter(url_nota=url_nota_recebida).exists():
                 return JsonResponse({'success': False, 'message': 'Bloqueado: Nota já registrada.'}, status=400)

            compra = form.save(commit=False)
            if url_nota_recebida:
                compra.url_nota = url_nota_recebida
                chave_encontrada = re.search(r'\d{44}', url_nota_recebida)
                if chave_encontrada: compra.chave_acesso = chave_encontrada.group()
            
            compra.save()
            
            count_estoque = 0
            count_criados = 0
            
            if itens_triagem_json:
                try:
                    itens = json.loads(itens_triagem_json)
                    produtos_lista = []

                    for item in itens:
                        nome = item.get('nome')
                        qtd = converter_para_float(item.get('quantidade'))
                        preco = converter_para_float(item.get('preco_unitario'))
                        
                        unidade_str = item.get('unidade', 'UN').strip()
                        unidade_obj = Unidade.objects.filter(sigla__iexact=unidade_str).first()
                        if not unidade_obj: unidade_obj = Unidade.objects.create(sigla=unidade_str.upper())

                        destino_tipo = item.get('destino_tipo')
                        destino_id = item.get('destino_id')
                        foi_pro_estoque = False

                        # Lógica de criação no estoque (CASA, PET, USER)
                        if destino_tipo == 'CASA' and destino_id:
                            try:
                                comodo_obj = Comodo.objects.get(id=destino_id)
                                local_obj = Localizacao.objects.filter(comodo=comodo_obj).first()
                                filho = ItemCasa.objects.create(
                                    nome=nome, comodo=comodo_obj, localizacao=local_obj,
                                    quantidade=qtd, preco=preco, unidade=unidade_obj,
                                    estoque_minimo=1, estoque_ideal=2
                                )
                                Estoque.objects.create(setor='CASA', item_casa=filho)
                                foi_pro_estoque = True; count_estoque += 1
                            except: pass

                        elif destino_tipo == 'PET' and destino_id:
                            try:
                                pet_obj = Pet.objects.get(id=destino_id)
                                filho = ItemPet.objects.create(
                                    nome=nome, pet=pet_obj, quantidade=qtd, preco=preco,
                                    unidade=unidade_obj, estoque_minimo=1, estoque_ideal=2
                                )
                                Estoque.objects.create(setor='PET', item_pet=filho)
                                foi_pro_estoque = True; count_estoque += 1
                            except: pass

                        elif destino_tipo == 'USUARIO' and destino_id:
                            try:
                                user_obj = User.objects.get(id=destino_id)
                                filho = ItemUsuario.objects.create(
                                    nome=nome, usuario=user_obj, quantidade=qtd,
                                    estoque_minimo=1, estoque_ideal=2
                                )
                                Estoque.objects.create(setor='USUARIO', item_usuario=filho)
                                foi_pro_estoque = True; count_estoque += 1
                            except: pass

                        produtos_lista.append(ListaCompraProduto(
                            compra=compra, nome=nome, quantidade=qtd, unidade=unidade_obj,
                            valor_unit=preco, adicionado_ao_estoque=foi_pro_estoque
                        ))
                        count_criados += 1

                    if produtos_lista:
                        ListaCompraProduto.objects.bulk_create(produtos_lista)

                except Exception as e:
                    compra.delete()
                    return JsonResponse({'success': False, 'message': f'Erro itens: {str(e)}'}, status=400)

            msg = f'Compra registrada ({count_criados} itens).'
            return JsonResponse({'success': True, 'message': msg})
        
        return JsonResponse({'success': False, 'errors': json.loads(form.errors.as_json())}, status=400)
    return JsonResponse({'success': False})

@login_required
@require_POST
@admin_required
def deletar_compra_ajax(request, pk):
    get_object_or_404(ListaCompra, pk=pk).delete()
    return JsonResponse({'success': True, 'message': 'Excluída.'})

@login_required
@require_POST
@admin_required
def editar_compra_ajax(request, pk):
    # 1. Busca a compra no banco
    c = get_object_or_404(ListaCompra, pk=pk)
    
    # 2. Cria uma cópia mutável dos dados que vieram do formulário (HTML)
    dados = request.POST.copy()
    
    # 3. TRUQUE DE MESTRE: 
    # Injetamos manualmente o 'valor_total' que já existe no banco dentro dos dados do formulário.
    # Assim, o Django valida com sucesso, mantendo o total original inalterado.
    dados['valor_total'] = c.valor_total
    
    # 4. Passa os dados completos (com o total injetado) para o Form
    form = ListaCompraForm(dados, instance=c)
    
    if form.is_valid(): 
        form.save()
        return JsonResponse({'success': True, 'message': 'Atualizado com sucesso!'})
    
    # Se ainda der erro, retorna o motivo (ex: Data inválida)
    return JsonResponse({'success': False, 'errors': json.loads(form.errors.as_json())}, status=400)

@login_required
def get_compra_json(request, pk):
    c = get_object_or_404(ListaCompra, pk=pk)
    return JsonResponse({'supermercado': c.supermercado, 'cidade': c.cidade, 'data_compra': c.data_compra.strftime('%Y-%m-%d'), 'valor_total': str(c.valor_total), 'detalhada': c.detalhada})

@login_required
def get_compra_itens_json(request, pk):
    compra = get_object_or_404(ListaCompra, pk=pk)
    itens = compra.produtos.all()
    dados_itens = []
    for i in itens:
        local_nome = "-"
        if i.comodo_destino:
            local_nome = i.comodo_destino.nome
            if i.comodo_destino.imovel:
                local_nome += f" ({i.comodo_destino.imovel.nome})"
        
        dados_itens.append({
            'nome': i.nome, 'quantidade': i.quantidade, 'unidade': i.unidade.sigla if i.unidade else 'UN',
            'valor_unit': i.valor_unit, 'total': i.quantidade * i.valor_unit, 'local': local_nome
        })
    return JsonResponse({'supermercado': compra.supermercado, 'data': compra.data_compra.strftime('%d/%m/%Y'), 'itens': dados_itens})

@login_required
@admin_required
def lista_compra_detalhe(request, pk):
    compra = get_object_or_404(ListaCompra, pk=pk)
    if request.method == 'POST':
        form = ListaCompraProdutoForm(request.POST)
        if form.is_valid():
            p = form.save(commit=False)
            p.compra = compra
            p.save()
            if form.cleaned_data.get('adicionar_ao_estoque'):
                try:
                    filho = ItemCasa.objects.create(
                        nome=p.nome, comodo=form.cleaned_data.get('comodo_destino'),
                        unidade=p.unidade, preco=p.valor_unit, quantidade=p.quantidade
                    )
                    Estoque.objects.create(setor='CASA', item_casa=filho)
                    p.adicionado_ao_estoque = True; p.save()
                except: pass
            return redirect('estoque:lista_compra_detalhe', pk=pk)
    else: form = ListaCompraProdutoForm()
    return render(request, 'estoque/lista_compra_detalhe.html', {'compra': compra, 'produtos': compra.produtos.all(), 'form_produto': form})

# ===================================================================
# 3. FINANCEIRO & HISTÓRICO
# ===================================================================

@login_required
@require_POST
@admin_required
def lancar_despesa_compra_ajax(request, pk):
    c = get_object_or_404(ListaCompra, pk=pk)
    if c.lancamento_financeiro_criado: return JsonResponse({'success':False})
    form = LancarDespesaCompraForm(request.POST, usuario=request.user)
    if form.is_valid():
        Financa.objects.create(
            conta=form.cleaned_data['conta'], usuario=request.user, 
            nome=f"Compra {c.supermercado}", tipo='Despesas', conta_tipo='Variadas', 
            valor=c.valor_total, data_registro=c.data_compra, compra_associada=c
        )
        c.lancamento_financeiro_criado = True; c.save()
        return JsonResponse({'success':True})
    return JsonResponse({'success':False})

@login_required
@require_POST
@admin_required
def reverter_lancamento_compra_ajax(request, pk):
    c = get_object_or_404(ListaCompra, pk=pk)
    if not c.lancamento_financeiro_criado: return JsonResponse({'success':False})
    Financa.objects.filter(compra_associada=c).delete()
    c.lancamento_financeiro_criado = False; c.save()
    return JsonResponse({'success':True})

@login_required
def aba_historico_estoque_partial(request):
    # Captura todos os filtros
    imovel_id = request.GET.get('imovel_id')
    setor = request.GET.get('setor', 'TODOS')
    owner_id = request.GET.get('owner_id')       # Filtro dinâmico (Cômodo/Pet/Usuário Dono)
    acao = request.GET.get('acao')               # Filtro de Tipo de Movimento
    usuario_log = request.GET.get('usuario_log') # Filtro de Quem Fez a ação

    # 1. Base da Query
    qs = HistoricoEstoque.objects.select_related(
        'usuario', 
        'estoque__item_casa__comodo__imovel',
        'estoque__item_pet__pet',
        'estoque__item_usuario__usuario'
    ).order_by('-data_movimento')

    # 2. Filtro: SETOR
    if setor != 'TODOS':
        qs = qs.filter(estoque__setor=setor)

    # 3. Filtro: IMÓVEL GLOBAL
    if imovel_id and imovel_id != 'TODOS' and str(imovel_id).isdigit():
        qs = qs.filter(
            Q(estoque__item_casa__comodo__imovel_id=int(imovel_id)) | 
            Q(estoque__setor__in=['PET', 'USUARIO'])
        )

    # 4. Filtro: AÇÃO (Criação, Baixa...)
    if acao:
        qs = qs.filter(tipo_movimento=acao)

    # 5. Filtro: USUÁRIO DO SISTEMA (Quem clicou no botão)
    if usuario_log and str(usuario_log).isdigit():
        qs = qs.filter(usuario_id=int(usuario_log))

    # 6. Filtro: DONO/LOCAL ESPECÍFICO (A mágica do filtro dinâmico)
    if owner_id and str(owner_id).isdigit():
        if setor == 'CASA':
            # Se for casa, owner_id é o ID do Cômodo
            qs = qs.filter(estoque__item_casa__comodo_id=int(owner_id))
        elif setor == 'PET':
            # Se for pet, owner_id é o ID do Pet
            qs = qs.filter(estoque__item_pet__pet_id=int(owner_id))
        elif setor == 'USUARIO':
            # Se for item pessoal, owner_id é o ID do Dono do item
            qs = qs.filter(estoque__item_usuario__usuario_id=int(owner_id))

    return render(request, 'partials/_tabela_historico_estoque.html', {'historico': qs[:200]})

# ===================================================================
# 4. SIMULAÇÃO & IMPORTAÇÃO LEGADA
# ===================================================================

@login_required
def importar_nota_view(request):
    return render(request, 'estoque/importar_nota.html')

@login_required
def processar_importacao_view(request):
    # (Código legado mantido)
    if request.method == "POST":
        url = request.POST.get('url_nota')
        resultado = importar_nota_sp(url)
        if not resultado['sucesso']:
            messages.error(request, resultado.get('erro', 'Erro desconhecido.'))
            return redirect('estoque:importar_nota')
        return render(request, 'estoque/revisar_importacao.html', {'mercado': resultado['mercado'], 'itens_nota': resultado['itens']})
    return redirect('estoque:importar_nota')

@login_required
@admin_required
def aba_simulacao_partial(request):
    imovel_id = request.GET.get('imovel_id')
    
    # 1. Base da Query
    qs = Estoque.objects.select_related(
        'item_casa__comodo__imovel', 
        'item_pet', 
        'item_usuario'
    ).order_by('item_casa__comodo__imovel__nome', 'item_casa__nome')

    # 2. Filtro Global de Imóvel nos ALERTAS
    if imovel_id and imovel_id != 'TODOS' and str(imovel_id).isdigit():
        qs = qs.filter(
            Q(item_casa__comodo__imovel_id=int(imovel_id)) | 
            Q(setor__in=['PET', 'USUARIO'])
        )
    else:
        qs = qs.exclude(item_casa__comodo__imovel__finalidade__in=['ALUGUEL', 'VENDA'])

    # 3. Processamento dos Alertas (Estoque Baixo + Validade)
    sugestoes_por_local = {}
    
    # --- NOVAS LISTAS PARA VALIDADE ---
    itens_vencidos = []
    itens_proximos = []
    hoje = timezone.localdate()
    # ----------------------------------

    total_atual = 0
    total_ideal = 0
    
    for estoque in qs:
        item = estoque.get_detalhe 
        if not item: continue

        # Dados Básicos
        preco = getattr(item, 'preco', 0)
        qtd = getattr(item, 'quantidade', 0)
        est_min = getattr(item, 'estoque_minimo', 0)
        est_ideal = getattr(item, 'estoque_ideal', 0)
        
        # --- CÁLCULO FINANCEIRO ---
        total_atual += (qtd * preco)
        total_ideal += (est_ideal * preco)

        # --- LÓGICA 1: VALIDADE (NOVO) ---
        validade = getattr(item, 'validade', None)
        if validade:
            # Calcula a diferença em dias
            dias_restantes = (validade - hoje).days
            
            # Injeta esse valor no objeto temporariamente para usar no Template
            item.dias_para_vencer = dias_restantes
            
            if dias_restantes < 0:
                itens_vencidos.append(item)
            elif dias_restantes <= 30: # Alerta se vencer em 30 dias ou menos
                itens_proximos.append(item)

        # --- LÓGICA 2: ESTOQUE BAIXO ---
        if qtd < est_min:
            nome_local = "Geral"
            
            if estoque.setor == 'CASA' and item.comodo:
                if not imovel_id or imovel_id == 'TODOS':
                    nome_casa = item.comodo.imovel.nome if item.comodo.imovel else "Sem Casa"
                    nome_local = f"{nome_casa} - {item.comodo.nome}"
                else:
                    nome_local = item.comodo.nome
            elif estoque.setor == 'PET':
                nome_local = f"Pets ({item.pet.nome_pet})"
            elif estoque.setor == 'USUARIO':
                nome_local = f"Pessoal ({item.usuario.username})"

            if nome_local not in sugestoes_por_local:
                sugestoes_por_local[nome_local] = []
            
            sugestoes_por_local[nome_local].append({
                'nome': item.nome,
                'atual': qtd,
                'minimo': est_min,
                'unidade': getattr(item.unidade, 'sigla', 'UN') if hasattr(item, 'unidade') else 'UN',
                'sugestao_compra': est_ideal - qtd
            })

    # =========================================================
    # PARTE 2: HUB DE REPOSIÇÃO (Filtrado)
    # =========================================================
    faltantes_qs = ItemFaltante.objects.select_related(
        'item_catalogo', 'usuario', 'pet', 'localizacao', 'comodo', 'unidade'
    ).order_by('-prioridade', '-data_adicionado')

    if imovel_id and imovel_id != 'TODOS' and str(imovel_id).isdigit():
        faltantes_qs = faltantes_qs.filter(
            Q(comodo__imovel_id=int(imovel_id)) | 
            Q(item_catalogo__setor__in=['PET', 'USUARIO'])
        )
    else:
        faltantes_qs = faltantes_qs.exclude(comodo__imovel__finalidade__in=['ALUGUEL', 'VENDA'])

    # Contexto Final
    progresso = (total_atual / total_ideal * 100) if total_ideal > 0 else 0

    context = {
        'itens_simulacao': qs, 
        'sugestoes_por_local': sugestoes_por_local, 
        
        # --- NOVOS DADOS NO CONTEXTO ---
        'itens_vencidos': itens_vencidos,
        'itens_proximos': itens_proximos,
        # -------------------------------

        'total_atual': total_atual,
        'total_ideal': total_ideal,
        'progresso': round(progresso, 1),
        'form_faltante': ItemFaltanteForm(), 
        'form_catalogo': CatalogoPessoalForm(),
        'itens_faltantes_marcados': faltantes_qs[:20] 
    }
    
    return render(request, 'partials/_aba_simulacao.html', context)

@login_required
@require_POST
def adicionar_item_faltante(request):
    form = ItemFaltanteForm(request.POST)
    if form.is_valid():
        try:
            d = form.cleaned_data
            destinos = d['destinatarios']
            ids = []
            if 'TODOS' in destinos:
                if d['setor_destino'] == 'USUARIO': ids = [u.id for u in User.objects.all()]
                elif d['setor_destino'] == 'PET': ids = [p.id for p in Pet.objects.all()]
                elif d['setor_destino'] == 'CASA': ids = [l.id for l in Localizacao.objects.all()]
            else: ids = [int(x) for x in destinos if x != 'TODOS']

            for tid in ids:
                lookup = {'item_catalogo': d['item_catalogo']}
                if d['setor_destino'] == 'USUARIO': lookup['usuario_id'] = tid
                elif d['setor_destino'] == 'PET': lookup['pet_id'] = tid
                elif d['setor_destino'] == 'CASA':
                    loc = Localizacao.objects.get(id=tid)
                    lookup.update({'localizacao': loc, 'comodo': loc.comodo})
                
                ItemFaltante.objects.get_or_create(**lookup, defaults={
                    'prioridade': d['prioridade'], 'observacao': d['observacao'], 
                    'quantidade': converter_para_float(d['quantidade']), 'unidade': d['unidade']
                })
            return JsonResponse({'success': True, 'message': 'Adicionado!'})
        except Exception as e: return JsonResponse({'success': False, 'message': str(e)}, status=400)
    return JsonResponse({'success': False, 'errors': json.loads(form.errors.as_json())}, status=400)

@login_required
@admin_required
def gerenciar_catalogo_pessoal(request):
    form = CatalogoPessoalForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid(): form.save(); return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'errors': json.loads(form.errors.as_json())}, status=400)
    itens = CatalogoPessoal.objects.select_related('categoria').all().order_by('setor', 'nome')
    return render(request, 'estoque/gerenciar_catalogo_pessoal.html', {'form_catalogo': form, 'itens_catalogo': itens})

@login_required
@require_POST
def remover_item_faltante(request, pk):
    ItemFaltante.objects.filter(pk=pk).delete()
    return JsonResponse({'success': True})

@login_required
@admin_required
def simulacao_cenario_detalhe(request, pk):
    return redirect('estoque:gerenciar_estoque')

# ===================================================================
# 5. AJAX HELPERS (SELECTS DINÂMICOS)
# ===================================================================

@login_required
@admin_required
def get_categorias_por_setor(request):
    setor = request.GET.get('setor')
    qs = EstoqueCategoria.objects.all().order_by('nome_categoria')
    if setor == 'CASA': qs = qs.filter(segmentacao__nome_segmento__in=['Casa', 'Todos'])
    elif setor == 'USUARIO': qs = qs.filter(segmentacao__nome_segmento__in=['N_Usuarios', 'Todos', 'Usuarios'])
    elif setor == 'PET': qs = qs.filter(segmentacao__nome_segmento__in=['N_Pets', 'Todos', 'Pets'])
    return JsonResponse([{'id': c.id, 'nome_categoria': c.nome_categoria} for c in qs.distinct()], safe=False)

@login_required
def get_destinatarios_json(request):
    """
    Resolve o DESTINO no Hub de Reposição.
    Recebe 'imovel_id' para filtrar os cômodos corretamente.
    """
    setor = request.GET.get('setor', 'USUARIO')
    imovel_id = request.GET.get('imovel_id') # <--- ID DO FILTRO GLOBAL
    
    data = [{'id': 'TODOS', 'label': 'Todos deste grupo', 'type': 'all'}]
    
    if setor == 'USUARIO':
        for u in User.objects.all().order_by('username'): 
            data.append({'id': u.id, 'label': u.username, 'type': 'user'})
            
    elif setor == 'PET':
        for p in Pet.objects.all().order_by('nome_pet'): 
            data.append({'id': p.id, 'label': p.nome_pet, 'type': 'pet'})
            
    elif setor == 'CASA':
        qs = Localizacao.objects.select_related('comodo__imovel').order_by('comodo__imovel__nome', 'comodo__nome', 'nome')
        
        # FILTRO DE IMÓVEL APLICADO AQUI
        if imovel_id and imovel_id != 'TODOS' and str(imovel_id).isdigit():
            qs = qs.filter(comodo__imovel_id=int(imovel_id))
            # Formato Simples: "Cozinha > Armário"
            for loc in qs:
                data.append({'id': loc.id, 'label': f"{loc.comodo.nome} > {loc.nome}", 'type': 'local'})
        else:
            # Formato Completo: "Casa 1 - Cozinha > Armário"
            qs = qs.exclude(comodo__imovel__finalidade='ALUGUEL')
            for loc in qs:
                nome_imovel = loc.comodo.imovel.nome if loc.comodo.imovel else "Sem Imóvel"
                data.append({'id': loc.id, 'label': f"{nome_imovel} - {loc.comodo.nome} > {loc.nome}", 'type': 'local'})

    # Busca itens do catálogo para popular o outro dropdown (Item Mestre)
    itens = CatalogoPessoal.objects.filter(setor=setor).values('id', 'nome')
    
    return JsonResponse({'destinatarios': data, 'itens': list(itens)})

@login_required
def get_filtro_opcoes(request):
    """
    Retorna opções para o segundo select (Cômodos/Locais).
    Lógica:
    - Se Imóvel X selecionado: Traz APENAS cômodos do Imóvel X.
    - Se Todos selecionado: Traz TUDO, mas com o nome da casa na frente.
    """
    setor = request.GET.get('setor')
    imovel_id = request.GET.get('imovel_id') # ID vindo do Javascript
    
    print(f"DEBUG: Carregando Opções | Setor: {setor} | Imóvel: {imovel_id}")

    opcoes = []

    if setor == 'USUARIO':
        qs = User.objects.all().order_by('username')
        opcoes = [{'id': u.id, 'text': u.username} for u in qs]
    
    elif setor == 'PET':
        qs = Pet.objects.all().order_by('nome_pet')
        opcoes = [{'id': p.id, 'text': p.nome_pet} for p in qs]
    
    elif setor == 'CASA':
        qs = Comodo.objects.select_related('imovel').order_by('imovel__nome', 'nome')
        
        # CENÁRIO 1: Imóvel Específico Selecionado
        if imovel_id and imovel_id != 'TODOS' and str(imovel_id).isdigit():
            # FILTRO EXCLUSIVO: Só traz cômodos desta casa
            qs = qs.filter(imovel_id=int(imovel_id))
            # Texto limpo: "Cozinha" (já sabemos que é da casa selecionada)
            opcoes = [{'id': c.id, 'text': c.nome} for c in qs]
            
        # CENÁRIO 2: Todos os Imóveis
        else:
            # Traz tudo, mas identifica: "Casa de Praia - Cozinha", "Apê - Sala"
            qs = qs.exclude(imovel__finalidade='ALUGUEL') 
            opcoes = [{'id': c.id, 'text': f"{c.imovel.nome} - {c.nome}"} for c in qs]

    return JsonResponse({'opcoes': opcoes})

@login_required
@admin_required
def get_localizacoes_json(request):
    """
    API para o dropdown de Localização (Dentro do cômodo).
    Ex: "Armário (Casa de Praia)", "Geladeira (Apê)"
    """
    comodo_id = request.GET.get('comodo_id')
    data = []
    
    if comodo_id:
        # Pega as localizações deste cômodo
        qs = Localizacao.objects.filter(comodo_id=comodo_id).select_related('comodo__imovel').order_by('nome')
        
        for l in qs:
            nome_display = l.nome
            # AQUI ESTÁ A MÁGICA: Adiciona o nome do imóvel ao lado da localização
            if l.comodo and l.comodo.imovel:
                nome_display = f"{l.nome} ({l.comodo.imovel.nome})"
            
            data.append({'id': l.id, 'nome': nome_display})
            
    return JsonResponse(data, safe=False)

@login_required
@admin_required
def get_comodos_por_imovel(request):
    """ 
    API para o dropdown em cascata (Imóvel -> Cômodo) 
    Retorna apenas os cômodos da casa selecionada.
    """
    imovel_id = request.GET.get('imovel_id')
    data = []
    
    if imovel_id and str(imovel_id).isdigit():
        # Filtra estritamente pelo ID do imóvel
        qs = Comodo.objects.filter(imovel_id=int(imovel_id)).order_by('nome')
        # Retorna: "Cozinha", "Sala"
        data = [{'id': c.id, 'nome': c.nome} for c in qs]
    else:
        # Se não tiver ID (ex: bug ou select vazio), não retorna nada para evitar erro
        pass

    return JsonResponse(data, safe=False)

# ===================================================================
# 6. APIS DE INTEGRAÇÃO (USADAS PELA ALIMENTAÇÃO)
# ===================================================================

@login_required
def api_get_locais_alimentos(request):
    """
    Retorna apenas localizações que tenham itens de 'Casa' (comida) com saldo positivo.
    VERSÃO BLINDADA: Não depende de related_name reverso.
    """
    try:
        # 1. Busca IDs de localizações que possuem itens com quantidade > 0
        # values_list com flat=True retorna uma lista limpa de IDs: [1, 5, 8]
        locais_ids = ItemCasa.objects.filter(quantidade__gt=0).values_list('localizacao_id', flat=True).distinct()
        
        # 2. Busca os objetos Localizacao baseados nesses IDs
        locais = Localizacao.objects.filter(id__in=locais_ids)
        
        data = []
        for loc in locais:
            # Navegação segura para evitar erro se comodo/imovel for None
            nome_comodo = loc.comodo.nome if loc.comodo else "Sem Cômodo"
            nome_imovel = "-"
            
            if loc.comodo and loc.comodo.imovel:
                nome_imovel = loc.comodo.imovel.nome
            
            data.append({
                'id': loc.id,
                'nome': loc.nome,      # Ex: Geladeira
                'comodo': nome_comodo, # Ex: Cozinha
                'imovel': nome_imovel  # Ex: Imovel 1
            })
        
        return JsonResponse(data, safe=False)

    except Exception as e:
        # Retorna lista vazia em caso de erro, para não travar o front
        print(f"Erro na API Locais: {e}")
        return JsonResponse([], safe=False)

@login_required
def api_get_itens_por_local(request, local_id):
    """
    Retorna os itens dentro daquela geladeira/armário.
    Usado pelo módulo de Alimentação.
    """
    # Filtra itens naquela localização que têm quantidade positiva
    itens = ItemCasa.objects.filter(localizacao_id=local_id, quantidade__gt=0)
    
    data = []
    for item in itens:
        sigla_unidade = item.unidade.sigla if item.unidade else 'UN'
        # Converter Decimal para float para o JSON
        saldo = float(item.quantidade)
        
        data.append({
            'id': item.id,
            'nome': item.nome,
            'saldo': saldo, 
            'unidade': sigla_unidade
        })
        
    return JsonResponse(data, safe=False)