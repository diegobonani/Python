import pygame
import sys
import random
import os
import requests
import threading
import re
from bs4 import BeautifulSoup
from gtts import gTTS
import time

# --- CONFIGURAÇÕES ---
pygame.init()
pygame.mixer.init()

# Aumentei a largura para caber a barra lateral
LARGURA, ALTURA = 1200, 720 
TELA = pygame.display.set_mode((LARGURA, ALTURA))
pygame.display.set_caption("Soletrando Show - Edição Profissional")

# Cores
AZUL_CENARIO = (0, 30, 80)
AZUL_LATERAL = (0, 20, 50) # Cor da barra lateral
AMARELO_OURO = (255, 215, 0)
BRANCO = (255, 255, 255)
VERDE = (0, 200, 0)
VERMELHO = (220, 0, 0)
CINZA_CLARO = (200, 200, 200)
PRETO = (0, 0, 0)

FONTE_TITULO = pygame.font.SysFont('arial', 40, bold=True)
FONTE_BOTAO = pygame.font.SysFont('arial', 20, bold=True)
FONTE_TEXTO = pygame.font.SysFont('arial', 24)
FONTE_LATERAL = pygame.font.SysFont('arial', 20)
FONTE_GRANDE = pygame.font.SysFont('arial', 50, bold=True)

# --- LISTAS MANUAIS (NÍVEIS INICIAIS) ---
PALAVRAS_FACIL = [
    "casa", "bola", "gato", "mesa", "pato", "dado", "faca", "leite", "sapo", "tatu",
    "vaca", "zero", "amor", "bala", "café", "dedo", "fogo", "gelo", "hoje", "ilha",
    "janela", "limão", "mola", "navio", "olho", "pipa", "queijo", "rato", "sala", "terra"
]

PALAVRAS_MEDIO = [
    "escola", "banana", "cidade", "boneca", "animal", "futebol", "girafa", "homem",
    "imagem", "jardim", "laranja", "macaco", "nuvem", "orelha", "sapato", "tapete",
    "violão", "xícara", "abacaxi", "baleia", "camisa", "dinheiro", "elefante", "foguete"
]

# --- UI ELEMENTOS ---
class CaixaNumero:
    def __init__(self, x, y, w, h, valor_inicial=2):
        self.rect = pygame.Rect(x, y, w, h)
        self.valor = valor_inicial
        self.ativo = False 
        tamanho_btn = h // 2
        self.btn_up = pygame.Rect(x + w, y, 30, tamanho_btn)
        self.btn_down = pygame.Rect(x + w, y + tamanho_btn, 30, tamanho_btn)
        
    def lidar_evento(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos): self.ativo = not self.ativo
            else: self.ativo = False
            if self.btn_up.collidepoint(event.pos): self.valor += 1
            elif self.btn_down.collidepoint(event.pos):
                if self.valor > 1: self.valor -= 1
        if event.type == pygame.KEYDOWN and self.ativo:
            if event.key == pygame.K_UP: self.valor += 1
            elif event.key == pygame.K_DOWN:
                if self.valor > 1: self.valor -= 1
            elif event.key == pygame.K_BACKSPACE:
                s = str(self.valor)[:-1]
                self.valor = int(s) if s else 0
            elif event.unicode.isdigit():
                s = str(self.valor) + event.unicode
                self.valor = int(s)

    def desenhar(self, tela):
        cor_borda = AMARELO_OURO if self.ativo else BRANCO
        pygame.draw.rect(tela, BRANCO, self.rect)
        pygame.draw.rect(tela, cor_borda, self.rect, 3)
        texto_surf = FONTE_TITULO.render(str(self.valor), True, PRETO)
        tela.blit(texto_surf, (self.rect.x + 10, self.rect.y + 5))
        
        mouse = pygame.mouse.get_pos()
        pygame.draw.rect(tela, CINZA_CLARO, self.btn_up); pygame.draw.rect(tela, PRETO, self.btn_up, 1)
        pygame.draw.polygon(tela, PRETO, [(self.btn_up.centerx, self.btn_up.centery-5), (self.btn_up.centerx-5, self.btn_up.centery+5), (self.btn_up.centerx+5, self.btn_up.centery+5)])
        pygame.draw.rect(tela, CINZA_CLARO, self.btn_down); pygame.draw.rect(tela, PRETO, self.btn_down, 1)
        pygame.draw.polygon(tela, PRETO, [(self.btn_down.centerx, self.btn_down.centery+5), (self.btn_down.centerx-5, self.btn_down.centery-5), (self.btn_down.centerx+5, self.btn_down.centery-5)])

# --- SISTEMAS AUXILIARES ---

class TratamentoTexto:
    @staticmethod
    def limpar_definicao(texto_bruto):
        texto_limpo = re.sub(r'^[a-z\.\s]+', '', texto_bruto) 
        texto_limpo = re.sub(r'\d+\.', '', texto_limpo)
        texto_limpo = re.sub(r'\[.*?\]', '', texto_limpo)
        return texto_limpo.strip().capitalize()

    @staticmethod
    def censurar_palavra_na_frase(frase, palavra):
        padrao = re.compile(re.escape(palavra), re.IGNORECASE)
        return padrao.sub("a palavra secreta", frase)

    @staticmethod
    def corrigir_nome_para_audio(nome):
        nome_tratado = nome.title()
        nome_tratado = nome_tratado.replace("lly", "li").replace("Lly", "Li")
        nome_tratado = nome_tratado.replace("Ello", "Elo")
        if nome_tratado.endswith("y"): nome_tratado = nome_tratado[:-1] + "i"
        return nome_tratado

class AudioSystem:
    @staticmethod
    def falar(texto):
        def _thread():
            try:
                tts = gTTS(text=texto, lang='pt', slow=False)
                arquivo = "temp_voz.mp3"
                if os.path.exists(arquivo):
                    try:
                        pygame.mixer.music.unload()
                        os.remove(arquivo)
                        time.sleep(0.1)
                    except: pass
                tts.save(arquivo)
                pygame.mixer.music.load(arquivo)
                pygame.mixer.music.play()
            except Exception as e:
                print(f"Erro TTS: {e}")
        threading.Thread(target=_thread, daemon=True).start()

class MotorDeBuscaInteligente:
    def verificar_qualidade_dicio(self, palavra):
        try:
            url = f"https://www.dicio.com.br/{palavra}/"
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers, timeout=3)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                div_def = soup.find(class_="significado")
                if not div_def: return None 
                txt_def = TratamentoTexto.limpar_definicao(div_def.get_text().strip().split('\n')[0])
                if len(txt_def) < 5: return None
                div_frase = soup.find(class_="frase")
                txt_frase = div_frase.get_text().strip() if div_frase else f"A palavra {palavra} é muito interessante."
                return {"def": txt_def, "ctx": txt_frase}
        except: pass
        return None

    def obter_fallback(self, palavra):
        # Tenta pegar definição de palavras manuais
        res = self.verificar_qualidade_dicio(palavra)
        if res: return {"palavra": palavra, "def": res['def'], "ctx": res['ctx']}
        return {"palavra": palavra, "def": "Definição indisponível.", "ctx": f"A palavra é {palavra}"}

    def gerar_palavra(self, nivel, streak_acertos):
        # 1. Níveis Manuais (Garante facilidade)
        if nivel == 1:
            return self.obter_fallback(random.choice(PALAVRAS_FACIL))
        elif nivel == 2:
            return self.obter_fallback(random.choice(PALAVRAS_MEDIO))
        
        # 2. Nível Difícil (API)
        min_len = 8 if nivel == 3 else 10
        tentativas = 0
        print(f"Buscando online... Nível {nivel}")
        
        while tentativas < 10:
            try:
                r = requests.get("https://api.dicionario-aberto.net/random", timeout=3)
                if r.status_code == 200:
                    palavra_crua = r.json().get('word', '').lower()
                    if '-' in palavra_crua or ' ' in palavra_crua: continue 
                    if len(palavra_crua) < min_len: continue
                    
                    dados = self.verificar_qualidade_dicio(palavra_crua)
                    if dados:
                        return {"palavra": palavra_crua, "def": dados["def"], "ctx": dados["ctx"]}
            except: pass
            tentativas += 1
            
        return self.obter_fallback("paralelepipedo")

# --- JOGO ---

class SoletrandoGame:
    def __init__(self):
        self.motor = MotorDeBuscaInteligente()
        self.estado = "MENU"
        self.jogadores = []
        self.nomes_temp = []
        self.qtd_target = 0
        self.idx_jogador = 0
        self.rodada_atual = {}
        self.texto_input = ""
        self.erro_digitado = ""
        self.erro_correto = ""
        self.texto_gestao = ""
        self.caixa_qtd = CaixaNumero(LARGURA//2 - 50, 350, 100, 60, valor_inicial=2)
        
        # Variáveis de Estado de Carregamento (Anti-Freeze)
        self.buscando_palavra = False

    # --- FLUXO DE MENU/CADASTRO ---
    def iniciar_cadastro(self):
        qtd = self.caixa_qtd.valor
        if qtd < 1: qtd = 1
        self.qtd_target = qtd
        self.nomes_temp = []
        self.texto_input = ""
        self.estado = "NOMES"
        AudioSystem.falar("Digite o nome do primeiro jogador.")

    def registrar_nome(self):
        nome = self.texto_input.strip()
        if not nome: return
        self.nomes_temp.append(nome)
        self.texto_input = ""
        nome_fala = TratamentoTexto.corrigir_nome_para_audio(nome)
        
        if len(self.nomes_temp) == self.qtd_target:
            AudioSystem.falar(f"Ok, {nome_fala}. Sorteando ordem...")
            self.finalizar_cadastro_e_sortear()
        else:
            AudioSystem.falar(f"Ok, {nome_fala}. Próximo.")

    def finalizar_cadastro_e_sortear(self):
        self.jogadores = [{"nome": n, "pontos": 0, "nivel": 1, "streak": 0} for n in self.nomes_temp]
        random.shuffle(self.jogadores)
        self.estado = "JOGANDO"
        # Inicia turno sem bloquear
        self.preparar_novo_turno(primeira_vez=True)

    # --- LÓGICA ANTI-FREEZE ---
    def preparar_novo_turno(self, primeira_vez=False):
        """Inicia a thread de busca"""
        if len(self.jogadores) == 0: return
        self.buscando_palavra = True
        self.texto_input = ""
        
        def _worker():
            jogador = self.jogadores[self.idx_jogador]
            # Busca pesada acontece aqui, sem travar tela
            self.rodada_atual = self.motor.gerar_palavra(jogador['nivel'], jogador['streak'])
            self.buscando_palavra = False
            
            # Quando terminar, dispara o áudio
            p = self.rodada_atual['palavra']
            nome_fala = TratamentoTexto.corrigir_nome_para_audio(jogador['nome'])
            intro = "Sorteio feito! " if primeira_vez else ""
            AudioSystem.falar(f"{intro}Vez de {nome_fala}. Nível {jogador['nivel']}. A palavra é... {p}.")

        threading.Thread(target=_worker, daemon=True).start()

    # --- AÇÕES DE JOGO ---
    def acao_ouvir_definicao(self):
        if not self.buscando_palavra:
            AudioSystem.falar(f"A definição é: {self.rodada_atual['def']}")

    def acao_ouvir_frase(self):
        if not self.buscando_palavra:
            frase = TratamentoTexto.censurar_palavra_na_frase(self.rodada_atual['ctx'], self.rodada_atual['palavra'])
            AudioSystem.falar(f"Aplicação na frase: {frase}")

    def acao_ouvir_palavra(self):
        if not self.buscando_palavra:
            AudioSystem.falar(f"A palavra é: {self.rodada_atual['palavra']}")

    def verificar_resposta(self):
        if self.buscando_palavra: return # Não deixa dar enter se tá carregando

        digitado = self.texto_input.strip().lower()
        correto = self.rodada_atual['palavra'].strip().lower()
        jogador = self.jogadores[self.idx_jogador]
        nome_fala = TratamentoTexto.corrigir_nome_para_audio(jogador['nome'])
        
        if digitado == correto:
            AudioSystem.falar(f"Acertou, {nome_fala}!")
            jogador['pontos'] += 10 * jogador['nivel']
            jogador['streak'] += 1
            # Lógica de subir nível
            if jogador['nivel'] == 1 and jogador['streak'] >= 3: jogador['nivel'] = 2
            elif jogador['nivel'] == 2 and jogador['streak'] >= 4: jogador['nivel'] = 3
            
            pygame.display.update()
            pygame.time.delay(2000)
            self.proximo_jogador(eliminar=False)
        else:
            self.erro_digitado = self.texto_input
            self.erro_correto = correto
            self.estado = "FEEDBACK_ERRO"
            AudioSystem.falar(f"Errou, {nome_fala}. Aperte Enter para corrigir.")

    def confirmar_erro_e_sair(self):
        self.proximo_jogador(eliminar=True)

    def proximo_jogador(self, eliminar):
        if eliminar and len(self.jogadores) > 0:
            self.jogadores.pop(self.idx_jogador)
            if self.idx_jogador >= len(self.jogadores):
                self.idx_jogador = 0
        else:
            self.idx_jogador = (self.idx_jogador + 1) % len(self.jogadores)

        if len(self.jogadores) == 1:
            self.estado = "VITORIA"
            n = TratamentoTexto.corrigir_nome_para_audio(self.jogadores[0]['nome'])
            AudioSystem.falar(f"Temos um vencedor! Parabéns {n}!")
        elif len(self.jogadores) == 0:
            self.estado = "MENU"
        else:
            self.estado = "JOGANDO"
            self.preparar_novo_turno()

    # --- GESTÃO ---
    def abrir_gestao(self):
        self.estado_anterior = self.estado
        self.estado = "GESTAO"
        self.texto_gestao = ""
        AudioSystem.falar("Gestão de Jogadores.")

    def acao_gestao(self):
        entrada = self.texto_gestao.strip()
        if entrada.upper() == "REMOVER":
            if self.jogadores:
                removido = self.jogadores.pop(self.idx_jogador)
                AudioSystem.falar(f"{removido['nome']} removido.")
                if self.idx_jogador >= len(self.jogadores): self.idx_jogador = 0
                
                if not self.jogadores: self.estado = "MENU"
                else: 
                    self.estado = "JOGANDO"
                    self.preparar_novo_turno()
            return

        if entrada:
            self.jogadores.append({"nome": entrada, "pontos": 0, "nivel": 1, "streak": 0})
            AudioSystem.falar(f"{entrada} entrou.")
            self.texto_gestao = ""

# --- UI FUNÇÕES ---

def desenhar_botao(tela, texto, x, y, w, h, cor, func=None):
    mouse = pygame.mouse.get_pos()
    click = pygame.mouse.get_pressed()
    cor_uso = (min(cor[0]+40, 255), min(cor[1]+40, 255), min(cor[2]+40, 255)) if (x < mouse[0] < x+w and y < mouse[1] < y+h) else cor
    pygame.draw.rect(tela, cor_uso, (x, y, w, h), border_radius=10)
    txt_surf = FONTE_BOTAO.render(texto, True, BRANCO)
    tela.blit(txt_surf, (x + w/2 - txt_surf.get_width()/2, y + h/2 - txt_surf.get_height()/2))
    if x < mouse[0] < x+w and y < mouse[1] < y+h and click[0] == 1 and func:
        func(); pygame.time.delay(250)

def desenhar_sidebar(tela, game):
    # Fundo Lateral
    pygame.draw.rect(tela, AZUL_LATERAL, (900, 0, 300, 720))
    pygame.draw.line(tela, AMARELO_OURO, (900, 0), (900, 720), 3)
    
    lbl = FONTE_BOTAO.render("JOGADORES", True, AMARELO_OURO)
    tela.blit(lbl, (1050 - lbl.get_width()//2, 20))
    
    y = 70
    for i, p in enumerate(game.jogadores):
        cor_nome = VERDE if i == game.idx_jogador else BRANCO
        prefixo = "-> " if i == game.idx_jogador else ""
        
        texto_nome = f"{prefixo}{p['nome']}"
        texto_info = f"Nv.{p['nivel']} | {p['pontos']}pts"
        
        # Desenha nome
        surf_nome = FONTE_LATERAL.render(texto_nome, True, cor_nome)
        tela.blit(surf_nome, (920, y))
        
        # Desenha info
        surf_info = FONTE_LATERAL.render(texto_info, True, CINZA_CLARO)
        tela.blit(surf_info, (920, y + 25))
        
        y += 60 # Espaçamento

def main():
    game = SoletrandoGame()
    clock = pygame.time.Clock()
    rodando = True
    
    while rodando:
        TELA.fill(BRANCO)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: rodando = False
            
            if game.estado == "MENU": game.caixa_qtd.lidar_evento(event)

            if event.type == pygame.KEYDOWN:
                # Tecla de Atalho J
                if event.key == pygame.K_j and game.estado in ["JOGANDO", "GESTAO"]:
                    if game.estado == "GESTAO": game.estado = "JOGANDO"
                    else: game.abrir_gestao()

                if game.estado == "NOMES":
                    if event.key == pygame.K_RETURN: game.registrar_nome()
                    elif event.key == pygame.K_BACKSPACE: game.texto_input = game.texto_input[:-1]
                    else: game.texto_input += event.unicode
                elif game.estado == "JOGANDO" and not game.buscando_palavra:
                    if event.key == pygame.K_RETURN: game.verificar_resposta()
                    elif event.key == pygame.K_BACKSPACE: game.texto_input = game.texto_input[:-1]
                    else: game.texto_input += event.unicode
                elif game.estado == "FEEDBACK_ERRO":
                    if event.key == pygame.K_RETURN: game.confirmar_erro_e_sair()
                elif game.estado == "GESTAO":
                    if event.key == pygame.K_RETURN: game.acao_gestao()
                    elif event.key == pygame.K_BACKSPACE: game.texto_gestao = game.texto_gestao[:-1]
                    else: game.texto_gestao += event.unicode

        # --- RENDERIZAÇÃO ---
        
        if game.estado == "MENU":
            TELA.fill(AZUL_CENARIO)
            txt = FONTE_TITULO.render("SOLETRANDO - SHOW", True, AMARELO_OURO)
            TELA.blit(txt, (LARGURA/2 - txt.get_width()/2, 100))
            game.caixa_qtd.desenhar(TELA)
            desenhar_botao(TELA, "INICIAR CADASTRO", LARGURA/2 - 120, 450, 240, 60, VERDE, game.iniciar_cadastro)

        elif game.estado == "NOMES":
            TELA.fill(AZUL_CENARIO)
            lbl = FONTE_TITULO.render(f"Nome do Jogador {len(game.nomes_temp) + 1}:", True, AMARELO_OURO)
            TELA.blit(lbl, (LARGURA/2 - lbl.get_width()/2, 200))
            pygame.draw.rect(TELA, BRANCO, (300, 300, 600, 70), border_radius=10)
            txt_surf = FONTE_TITULO.render(game.texto_input, True, PRETO)
            TELA.blit(txt_surf, (LARGURA/2 - txt_surf.get_width()/2, 310))
            desenhar_botao(TELA, "CONFIRMAR", LARGURA/2 - 100, 450, 200, 60, VERDE, game.registrar_nome)

        elif game.estado == "JOGANDO":
            TELA.fill(AZUL_CENARIO)
            
            # Se estiver buscando palavra na thread, mostra loading
            if game.buscando_palavra:
                loading = FONTE_GRANDE.render("BUSCANDO PALAVRA...", True, AMARELO_OURO)
                TELA.blit(loading, (300, 300))
            else:
                # Elementos do Jogo
                desenhar_botao(TELA, "OUVIR PALAVRA", 100, 150, 250, 70, (0, 100, 200), game.acao_ouvir_palavra)
                desenhar_botao(TELA, "OUVIR DEFINIÇÃO", 375, 150, 250, 70, (255, 140, 0), game.acao_ouvir_definicao)
                desenhar_botao(TELA, "OUVIR APLICAÇÃO", 650, 150, 250, 70, (255, 140, 0), game.acao_ouvir_frase)
                
                # Área de Input (deslocada para esquerda para não bater na sidebar)
                pygame.draw.rect(TELA, BRANCO, (150, 400, 600, 60), border_radius=10)
                TELA.blit(FONTE_TITULO.render(game.texto_input, True, PRETO), (170, 410))
                
                info_j = FONTE_TEXTO.render("Pressione J para Menu de Gestão", True, CINZA_CLARO)
                TELA.blit(info_j, (150, 650))

            # Barra Lateral (Sempre visível)
            desenhar_sidebar(TELA, game)

        elif game.estado == "FEEDBACK_ERRO":
            TELA.fill(VERMELHO)
            lbl_ops = FONTE_GRANDE.render("OPS! VOCÊ ERROU!", True, BRANCO)
            TELA.blit(lbl_ops, (400, 100))
            
            pygame.draw.rect(TELA, BRANCO, (100, 250, 700, 300), border_radius=20)
            
            TELA.blit(FONTE_TEXTO.render(f"Você escreveu:", True, PRETO), (150, 280))
            TELA.blit(FONTE_TITULO.render(f"{game.erro_digitado}", True, VERMELHO), (150, 320))
            
            TELA.blit(FONTE_TEXTO.render(f"A forma correta é:", True, PRETO), (150, 400))
            TELA.blit(FONTE_GRANDE.render(f"{game.erro_correto}", True, VERDE), (150, 440))
            
            TELA.blit(FONTE_BOTAO.render("Pressione ENTER para continuar...", True, CINZA_CLARO), (250, 600))
            
            desenhar_sidebar(TELA, game)

        elif game.estado == "GESTAO":
            # Fundo transparente
            s = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
            s.fill((0,0,0, 220)); TELA.blit(s, (0,0))
            
            # Painel
            pygame.draw.rect(TELA, BRANCO, (200, 150, 500, 400), border_radius=20)
            TELA.blit(FONTE_TITULO.render("GESTÃO", True, AZUL_CENARIO), (350, 180))
            TELA.blit(FONTE_TEXTO.render("Digite NOME para entrar", True, PRETO), (250, 250))
            TELA.blit(FONTE_TEXTO.render("Ou 'REMOVER' para sair", True, VERMELHO), (250, 290))
            
            pygame.draw.rect(TELA, CINZA_CLARO, (250, 350, 400, 60))
            TELA.blit(FONTE_TITULO.render(game.texto_gestao, True, PRETO), (260, 360))
            
            desenhar_botao(TELA, "CONFIRMAR", 330, 450, 240, 60, VERDE, game.acao_gestao)
            TELA.blit(FONTE_BOTAO.render("Pressione J para voltar", True, PRETO), (350, 530))
            
            desenhar_sidebar(TELA, game)

        elif game.estado == "VITORIA":
            TELA.fill(AZUL_CENARIO)
            venc = game.jogadores[0]
            TELA.blit(FONTE_GRANDE.render("CAMPEÃO!", True, AMARELO_OURO), (350, 200))
            TELA.blit(FONTE_TITULO.render(venc['nome'], True, BRANCO), (400, 300))
            desenhar_botao(TELA, "MENU", 350, 500, 250, 60, VERDE, lambda: setattr(game, 'estado', 'MENU'))

        pygame.display.update()
        clock.tick(30)
    pygame.quit(); sys.exit()

if __name__ == "__main__":
    main()