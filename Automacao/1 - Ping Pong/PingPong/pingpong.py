import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
import random
import itertools
import threading
import time
import json
import os
import math
from datetime import datetime

# Importa som nativo do Windows para teste de hardware
try:
    import winsound
except ImportError:
    winsound = None

# --- CONFIGURAÇÃO GLOBAL DE ÁUDIO ---
TEM_MIC = False
TEM_FALA = False
engine = None

# Inicializa SpeechRecognition
try:
    import speech_recognition as sr
    TEM_MIC = True
except ImportError: pass

# Inicializa Pyttsx3
try:
    import pyttsx3
    TEM_FALA = True
    engine = pyttsx3.init()
    engine.setProperty('rate', 180)
    # Tenta pegar voz PT-BR padrão
    try:
        voices = engine.getProperty('voices')
        for v in voices:
            if "brazil" in v.name.lower() or "portuguese" in v.name.lower():
                engine.setProperty('voice', v.id)
                break
    except: pass
except ImportError: pass

# Variáveis globais para seleção de driver
MIC_INDEX_SELECIONADO = None 
VOZ_ID_SELECIONADA = None

# --- BANCO DE DADOS ---
DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_JOGADORES = os.path.join(DIRETORIO_ATUAL, "jogadores.json")
ARQUIVO_HISTORICO = os.path.join(DIRETORIO_ATUAL, "historico_partidas.json")

class BancoDados:
    @staticmethod
    def carregar_jogadores():
        if not os.path.exists(ARQUIVO_JOGADORES): return []
        try:
            with open(ARQUIVO_JOGADORES, "r", encoding="utf-8") as f: return json.load(f)
        except: return []
    @staticmethod
    def salvar_jogadores(lista):
        with open(ARQUIVO_JOGADORES, "w", encoding="utf-8") as f: json.dump(lista, f, indent=4)
    @staticmethod
    def carregar_historico():
        if not os.path.exists(ARQUIVO_HISTORICO): return []
        try:
            with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f: return json.load(f)
        except: return []
    @staticmethod
    def salvar_historico(lista):
        with open(ARQUIVO_HISTORICO, "w", encoding="utf-8") as f: json.dump(lista, f, indent=4)
    @staticmethod
    def salvar_partida(p1, p2, s1, s2, vencedor, modo):
        hist = BancoDados.carregar_historico()
        reg = {
            "data_hora": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "data_filtro": datetime.now().strftime("%Y-%m-%d"),
            "p1": p1, "p2": p2, "s1": s1, "s2": s2, 
            "vencedor": vencedor, "modo": modo
        }
        hist.append(reg)
        BancoDados.salvar_historico(hist)

# --- CAIXA DE DIALOGO VOZ ---
class CaixaDialogoVoz:
    def __init__(self, master, titulo, mensagem):
        self.resultado = False
        self.ouvindo = True
        self.win = tk.Toplevel(master)
        self.win.title(titulo)
        self.win.geometry("400x250")
        self.win.config(bg="#222")
        self.win.transient(master)
        self.win.grab_set()
        
        try:
            x = master.winfo_x() + (master.winfo_width()//2) - 200
            y = master.winfo_y() + (master.winfo_height()//2) - 125
            self.win.geometry(f"+{x}+{y}")
        except: pass

        tk.Label(self.win, text="🎤 COMANDO DE VOZ", font=("Arial", 10, "bold"), bg="#222", fg="#FFC107").pack(pady=10)
        tk.Label(self.win, text=mensagem, font=("Arial", 12, "bold"), bg="#222", fg="white", wraplength=380).pack(pady=10)
        self.lbl_status = tk.Label(self.win, text="Escutando... Diga 'Sim' ou 'Não'", font=("Consolas", 10), bg="#000", fg="#0F0", width=40)
        self.lbl_status.pack(pady=10)

        f_btns = tk.Frame(self.win, bg="#222")
        f_btns.pack(pady=10)
        tk.Button(f_btns, text="SIM", command=self.confirmar, bg="#4CAF50", fg="white", width=10).pack(side="left", padx=10)
        tk.Button(f_btns, text="NÃO", command=self.cancelar, bg="#F44336", fg="white", width=10).pack(side="left", padx=10)

        if TEM_FALA: threading.Thread(target=self.falar_msg, args=(mensagem,), daemon=True).start()
        if TEM_MIC: threading.Thread(target=self.ouvir_loop, daemon=True).start()
        else: self.lbl_status.config(text="Mic off.", fg="red")
        master.wait_window(self.win)

    def falar_msg(self, msg):
        try:
            if VOZ_ID_SELECIONADA: engine.setProperty('voice', VOZ_ID_SELECIONADA)
            msg_limpa = msg.replace("\n", ". ").replace("x", "contra")
            engine.say(msg_limpa); engine.runAndWait()
        except: pass

    def ouvir_loop(self):
        r = sr.Recognizer()
        try:
            with sr.Microphone(device_index=MIC_INDEX_SELECIONADO) as s: r.adjust_for_ambient_noise(s, duration=0.5)
        except: return
        sims = ['sim', 'ok', 'pode', 'confirma', 'iniciar', 'vai', 'bora', 'yes']
        naos = ['não', 'nao', 'cancelar', 'fechar', 'para', 'voltar', 'no']
        while self.ouvindo:
            try:
                with sr.Microphone(device_index=MIC_INDEX_SELECIONADO) as s:
                    a = r.listen(s, timeout=3, phrase_time_limit=3)
                t = r.recognize_google(a, language="pt-BR").lower()
                self.lbl_status.config(text=f"Ouvi: '{t}'", fg="cyan")
                if any(p in t for p in sims): self.win.after(0, self.confirmar); break
                if any(p in t for p in naos): self.win.after(0, self.cancelar); break
            except: pass

    def confirmar(self):
        self.resultado = True; self.ouvindo = False; self.win.destroy()
    def cancelar(self):
        self.resultado = False; self.ouvindo = False; self.win.destroy()

# --- VISUALIZADOR DE CHAVES ---
class VisualizadorChaves:
    def __init__(self, master, arvore_dados):
        self.win = tk.Toplevel(master)
        self.win.title("🏆 Chaveamento Oficial")
        self.win.geometry("1100x650")
        self.canvas = tk.Canvas(self.win, bg="white")
        sb_y = tk.Scrollbar(self.win, orient="vertical", command=self.canvas.yview)
        sb_x = tk.Scrollbar(self.win, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)
        sb_y.pack(side="right", fill="y")
        sb_x.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.arvore = arvore_dados
        self.desenhar()

    def desenhar(self):
        self.canvas.delete("all")
        x_ini, y_ini, w_box, h_box, dist_x = 50, 80, 140, 40, 220
        conexoes = {}
        fases = ["Final", "Semifinal", "Quartas", "Oitavas", "1ª Fase"]
        
        for i in range(len(self.arvore)):
            idx_rev = len(self.arvore)-1-i
            tit = fases[idx_rev] if idx_rev < len(fases) else f"{idx_rev+1}ª Fase"
            cx = x_ini + (i*dist_x) + (w_box/2)
            self.canvas.create_text(cx, 40, text=tit, font=("Arial", 12, "bold"), fill="#555")

        for r_idx, rodada in enumerate(self.arvore):
            esp_y = 70 * (2**r_idx)
            y_start = y_ini + (35 * (2**r_idx))
            for m_idx, match in enumerate(rodada):
                cx, cy = x_ini + (r_idx*dist_x), y_start + (m_idx*esp_y)
                if r_idx > 0:
                    o1, o2 = conexoes.get((r_idx-1, m_idx*2)), conexoes.get((r_idx-1, (m_idx*2)+1))
                    if o1: self.canvas.create_line(o1[0], o1[1], cx, cy+h_box/2-10, fill="#999", width=2)
                    if o2: 
                        self.canvas.create_line(o2[0], o2[1], cx, cy+h_box/2+10, fill="#999", width=2)
                        self.canvas.create_line(cx, cy+h_box/2-10, cx, cy+h_box/2+10, fill="#999", width=2)
                    if o1 and not o2 and not match.get('p2'):
                        self.canvas.create_line(o1[0], o1[1], cx, cy+h_box/2, fill="#4CAF50", width=2, dash=(4,2))

                p1, p2, s1, s2, v = match.get('p1','???'), match.get('p2'), match.get('s1'), match.get('s2'), match.get('vencedor')
                fill1 = "#C8E6C9" if v==p1 and p1!="???" else "white"
                txt1 = f"{p1} ({s1})" if s1 is not None else p1
                self.canvas.create_rectangle(cx, cy, cx+w_box, cy+h_box, fill=fill1)
                self.canvas.create_text(cx+5, cy+h_box/2, text=txt1, anchor="w", font=("Arial",9,"bold" if s1 else "normal"))
                y_out = cy + h_box/2
                if p2:
                    fill2 = "#C8E6C9" if v==p2 and p2!="???" else "white"
                    txt2 = f"{p2} ({s2})" if s2 is not None else p2
                    self.canvas.create_rectangle(cx, cy+h_box, cx+w_box, cy+h_box*2, fill=fill2)
                    self.canvas.create_text(cx+5, cy+h_box*1.5, text=txt2, anchor="w", font=("Arial",9,"bold" if s2 else "normal"))
                    y_out = cy + h_box
                
                if r_idx == len(self.arvore)-1 and v:
                     self.canvas.create_text(cx + w_box/2, cy - 20, text="🏆 CAMPEÃO", fill="#FF9800", font=("Arial", 10, "bold"))
                conexoes[(r_idx, m_idx)] = (cx+w_box, y_out)
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

    def atualizar(self, dados):
        self.arvore = dados
        self.desenhar()
        self.win.update()

# --- JANELA PLACAR ---
class JanelaPlacarAoVivo:
    def __init__(self, master, p1, p2, cb, modo):
        self.master, self.p1, self.p2, self.cb, self.modo = master, p1, p2, cb, modo
        self.s1, self.s2, self.ouvindo, self.fila_fala, self.ja_finalizou = 0, 0, True, [], False
        self.win = tk.Toplevel(master)
        self.win.title("🔴 AO VIVO")
        self.win.geometry("950x750")
        self.win.config(bg="#111")
        self.win.protocol("WM_DELETE_WINDOW", self.tentar_fechar)
        self.criar_layout()
        if TEM_MIC: threading.Thread(target=self.ouvir, daemon=True).start()
        else: self.log("Microfone não detectado", "red")
        if TEM_FALA: threading.Thread(target=self.falar, daemon=True).start()
        self.master.wait_window(self.win)

    def criar_layout(self):
        tk.Label(self.win, text="ARENA", font=("Arial",20,"bold"), bg="#111", fg="#fff").pack(pady=10)
        frm = tk.Frame(self.win, bg="#111")
        frm.pack(expand=True, fill="both")
        
        f1 = tk.Frame(frm, bg="#222", bd=2, relief="ridge"); f1.pack(side="left", expand=True, fill="both", padx=10)
        tk.Label(f1, text=self.p1, font=("Arial",20), fg="#4CAF50", bg="#222").pack(pady=10)
        self.lbl1 = tk.Label(f1, text="0", font=("Impact",100), fg="#fff", bg="#222"); self.lbl1.pack()
        tk.Button(f1, text="+1", command=lambda: self.pt(1,1), bg="#4CAF50", fg="white", font=("bold", 14)).pack(pady=5)
        tk.Button(f1, text="-1", command=lambda: self.pt(1,-1), bg="#444", fg="white").pack()

        f2 = tk.Frame(frm, bg="#222", bd=2, relief="ridge"); f2.pack(side="left", expand=True, fill="both", padx=10)
        tk.Label(f2, text=self.p2, font=("Arial",20), fg="#2196F3", bg="#222").pack(pady=10)
        self.lbl2 = tk.Label(f2, text="0", font=("Impact",100), fg="#fff", bg="#222"); self.lbl2.pack()
        tk.Button(f2, text="+1", command=lambda: self.pt(2,1), bg="#2196F3", fg="white", font=("bold", 14)).pack(pady=5)
        tk.Button(f2, text="-1", command=lambda: self.pt(2,-1), bg="#444", fg="white").pack()
        
        self.info = tk.Label(self.win, text="", font=("Arial",16,"bold"), bg="#111", fg="orange"); self.info.pack(pady=5)
        cons = tk.LabelFrame(self.win, text="Status Voz", bg="black", fg="gray")
        cons.pack(fill="x", padx=10, pady=10)
        self.lbl_log = tk.Label(cons, text="Iniciando...", bg="black", fg="#0f0", anchor="w", font=("Consolas",10))
        self.lbl_log.pack(fill="x")
        tk.Button(self.win, text="ENCERRAR / W.O.", command=self.wo, bg="#D32F2F", fg="white").pack(pady=10)

    def log(self, t, c="#0f0"): 
        try: self.lbl_log.config(text=f"[{datetime.now().strftime('%H:%M:%S')}] {t}", fg=c)
        except: pass
    def narrar(self, t):
        if TEM_FALA: self.fila_fala.append(t)
    def falar(self):
        while self.ouvindo:
            if self.fila_fala:
                try: 
                    if VOZ_ID_SELECIONADA: engine.setProperty('voice', VOZ_ID_SELECIONADA)
                    engine.say(self.fila_fala.pop(0)); engine.runAndWait()
                except: pass
            time.sleep(0.1)

    def pt(self, p, d):
        if p==1: self.s1 = max(0, self.s1+d)
        else: self.s2 = max(0, self.s2+d)
        self.lbl1['text'], self.lbl2['text'] = str(self.s1), str(self.s2)
        self.info['text'] = ""
        p1, p2, diff = self.s1, self.s2, abs(self.s1-self.s2)
        if (p1>=11 or p2>=11) and diff>=2:
            w = self.p1 if p1>p2 else self.p2
            self.narrar(f"Vitória de {w}")
            messagebox.showinfo("Fim", f"Vencedor: {w}")
            BancoDados.salvar_partida(self.p1, self.p2, p1, p2, w, self.modo)
            self.fim(p1, p2)
            return
        mp1 = (p1+1>=11 and abs((p1+1)-p2)>=2)
        mp2 = (p2+1>=11 and abs((p2+1)-p1)>=2)
        if d>0:
            if mp1: self.info['text']="MATCH POINT P1"; self.narrar("Match Point")
            elif mp2: self.info['text']="MATCH POINT P2"; self.narrar("Match Point")
            elif p1>=10 and p2>=10 and diff==1: self.narrar("Vantagem")

    def ouvir(self):
        r = sr.Recognizer()
        try:
            with sr.Microphone(device_index=MIC_INDEX_SELECIONADO) as s:
                r.adjust_for_ambient_noise(s)
                self.log(f"Mic {MIC_INDEX_SELECIONADO} Ativo!", "#0f0")
                while self.ouvindo:
                    try:
                        a = r.listen(s, timeout=3, phrase_time_limit=3)
                        t = r.recognize_google(a, language="pt-BR").lower()
                        self.log(f"Ouvi: {t}", "cyan")
                        n1, n2 = self.p1.lower().split()[0], self.p2.lower().split()[0]
                        if "ponto" in t:
                            if n1 in t: self.win.after(0,lambda:self.pt(1,1)); self.log(f"Ponto {n1}", "#0f0")
                            elif n2 in t: self.win.after(0,lambda:self.pt(2,1)); self.log(f"Ponto {n2}", "#0f0")
                    except: pass
        except: self.log("Erro Mic (Verifique Diagnóstico)", "red")

    def wo(self):
        diag = CaixaDialogoVoz(self.win, "W.O.", "Confirmar W.O.? (Sim/Não)")
        if diag.resultado:
            w = self.p1 if self.s1 > self.s2 else self.p2
            BancoDados.salvar_partida(self.p1, self.p2, self.s1, self.s2, w, self.modo)
            self.fim(self.s1, self.s2)
    def tentar_fechar(self):
        diag = CaixaDialogoVoz(self.win, "Sair", "Cancelar torneio? (Sim/Não)")
        if diag.resultado: self.fim(-1,-1)
    def fim(self, s1, s2):
        if self.ja_finalizou: return
        self.ja_finalizou = True; self.ouvindo = False; self.win.destroy(); self.cb(self.p1, self.p2, s1, s2)

# --- APP PRINCIPAL ---
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Ping Pong Manager Pro")
        self.root.geometry("980x680")
        self.jogadores = BancoDados.carregar_jogadores()
        self.janela_aberta = False
        self.em_torneio = False 
        self.viz = None
        self.arvore_torneio = []
        
        style = ttk.Style(); style.theme_use('clam')
        container = tk.Frame(root); container.pack(fill="both", expand=True)
        
        self.sidebar = tk.Frame(container, bg="#2c3e50", width=200)
        self.sidebar.pack(side="left", fill="y"); self.sidebar.pack_propagate(False)
        tk.Label(self.sidebar, text="🏓 PING PONG", bg="#2c3e50", fg="white", font=("Arial", 16, "bold")).pack(pady=20)
        
        self.criar_bt("🏠 Início", self.show_inicio)
        self.criar_bt("🏆 Mata-Mata", self.iniciar_mata)
        self.criar_bt("📊 Grupos", self.iniciar_grupo)
        self.criar_bt("👑 Rei Mesa", self.iniciar_rei)
        tk.Frame(self.sidebar, height=2, bg="#34495e").pack(fill="x", pady=10)
        self.criar_bt("📈 Estatísticas", self.show_stats)
        self.criar_bt("⚙️ Config / Dados", self.show_config)
        self.criar_bt("🎤 Central de Voz", self.show_diag)

        self.content = tk.Frame(container, bg="#ecf0f1"); self.content.pack(side="left", fill="both", expand=True)
        self.f_inicio = tk.Frame(self.content, bg="#ecf0f1")
        self.f_stats = tk.Frame(self.content, bg="#ecf0f1")
        self.f_diag = tk.Frame(self.content, bg="#ecf0f1")
        self.f_config = tk.Frame(self.content, bg="#ecf0f1")
        
        self.setup_inicio(); self.setup_stats(); self.setup_diag(); self.setup_config(); self.show_inicio()

    def criar_bt(self, t, c):
        b = tk.Button(self.sidebar, text=t, command=c, bg="#2c3e50", fg="white", bd=0, font=("Arial", 11), anchor="w", padx=20, pady=10)
        b.pack(fill="x"); return b
    def limpar(self):
        for f in [self.f_inicio, self.f_stats, self.f_diag, self.f_config]: f.pack_forget()
    def show_inicio(self): self.limpar(); self.f_inicio.pack(fill="both", expand=True, padx=20, pady=20)
    def show_diag(self): self.limpar(); self.f_diag.pack(fill="both", expand=True, padx=20, pady=20)
    def show_stats(self): self.limpar(); self.f_stats.pack(fill="both", expand=True, padx=20, pady=20); self.recarregar_estatisticas()
    def show_config(self): self.limpar(); self.f_config.pack(fill="both", expand=True, padx=20, pady=20); self.atualizar_lista_config()

    # --- SETUP TELAS ---
    def setup_inicio(self):
        tk.Label(self.f_inicio, text="Jogadores", font=("Arial",18,"bold"), bg="#ecf0f1").pack(anchor="w")
        f = tk.LabelFrame(self.f_inicio, text="Novo", bg="#ecf0f1", padx=10, pady=10); f.pack(fill="x", pady=10)
        self.ent_nome = tk.Entry(f, width=20); self.ent_nome.pack(side="left", padx=5)
        self.ent_nome.bind("<Return>", lambda e: self.add())
        self.v_sexo = tk.StringVar(value="M")
        tk.Radiobutton(f, text="M", variable=self.v_sexo, value="M", bg="#ecf0f1").pack(side="left")
        tk.Radiobutton(f, text="F", variable=self.v_sexo, value="F", bg="#ecf0f1").pack(side="left")
        tk.Button(f, text="Add", command=self.add, bg="#27ae60", fg="white").pack(side="left", padx=10)
        self.lista = tk.Listbox(self.f_inicio, height=12, font=("Arial", 11)); self.lista.pack(fill="both", expand=True)
        fc = tk.LabelFrame(self.f_inicio, text="Filtros", bg="#ecf0f1"); fc.pack(fill="x", pady=10)
        self.cb_cat = ttk.Combobox(fc, values=["Misto (Todos)", "Apenas Masculino", "Apenas Feminino"], state="readonly")
        self.cb_cat.current(0); self.cb_cat.pack(anchor="w", padx=10, pady=5)
        self.cb_cat.bind("<<ComboboxSelected>>", lambda e: self.atualizar_lista())
        self.atualizar_lista()

    def add(self):
        n = self.ent_nome.get().strip()
        if n and not any(j['nome']==n for j in self.jogadores):
            self.jogadores.append({'nome':n, 'sexo':self.v_sexo.get()}); BancoDados.salvar_jogadores(self.jogadores); self.atualizar_lista(); self.ent_nome.delete(0,'end')
    def atualizar_lista(self):
        self.lista.delete(0,'end'); cat = self.cb_cat.get(); f = []
        for j in self.jogadores:
            if cat=="Misto (Todos)" or (cat=="Apenas Masculino" and j['sexo']=="M") or (cat=="Apenas Feminino" and j['sexo']=="F"): f.append(j)
        f.sort(key=lambda x: x['nome'].lower())
        for j in f: self.lista.insert('end', f"[{j['sexo']}] {j['nome']}")

    def setup_config(self):
        tk.Label(self.f_config, text="Gerenciamento", font=("bold",18), bg="#ecf0f1").pack(anchor="w", pady=10)
        lf1 = tk.LabelFrame(self.f_config, text="Editar Jogadores", bg="#ecf0f1", padx=10, pady=10); lf1.pack(fill="x", pady=10)
        self.lb_conf = tk.Listbox(lf1, height=6); self.lb_conf.pack(side="left", fill="x", expand=True, padx=5)
        fr = tk.Frame(lf1, bg="#ecf0f1"); fr.pack(side="left", fill="y")
        tk.Button(fr, text="✏️ Editar Nome", command=self.edit_n).pack(fill="x", pady=2)
        tk.Button(fr, text="⚧ Trocar Sexo", command=self.edit_s, bg="pink").pack(fill="x", pady=2)
        tk.Button(fr, text="🗑️ Excluir", command=self.del_j, bg="red", fg="white").pack(fill="x", pady=2)
        
    def atualizar_lista_config(self):
        self.lb_conf.delete(0, 'end')
        for j in sorted(self.jogadores, key=lambda x: x['nome'].lower()): self.lb_conf.insert('end', j['nome'])
    def get_sel_conf(self):
        if self.lb_conf.curselection(): return self.lb_conf.get(self.lb_conf.curselection()[0])
    def edit_n(self):
        n = self.get_sel_conf()
        if not n: return
        novo = simpledialog.askstring("Editar", "Nome:", initialvalue=n)
        if novo and novo!=n:
            for j in self.jogadores: 
                if j['nome']==n: j['nome']=novo; break
            BancoDados.salvar_jogadores(self.jogadores); self.atualizar_lista_config(); self.atualizar_lista()
    def edit_s(self):
        n = self.get_sel_conf()
        if not n: return
        for j in self.jogadores:
            if j['nome']==n: j['sexo'] = "F" if j['sexo']=="M" else "M"; break
        BancoDados.salvar_jogadores(self.jogadores); self.atualizar_lista_config(); self.atualizar_lista()
    def del_j(self):
        n = self.get_sel_conf()
        if n and messagebox.askyesno("Del", f"Excluir {n}?"):
            for i,j in enumerate(self.jogadores):
                if j['nome']==n: del self.jogadores[i]; break
            BancoDados.salvar_jogadores(self.jogadores); self.atualizar_lista_config(); self.atualizar_lista()

    def setup_diag(self):
        tk.Label(self.f_diag, text="Diagnóstico", font=("bold",18), bg="#ecf0f1").pack(anchor="w", pady=10)
        # Seletor Mic
        fm = tk.LabelFrame(self.f_diag, text="Entrada (Mic)", bg="#ecf0f1"); fm.pack(fill="x", pady=5)
        self.cb_mic = ttk.Combobox(fm, state="readonly", width=40); self.cb_mic.pack(side="left", padx=5)
        if TEM_MIC:
            try: 
                mics = sr.Microphone.list_microphone_names()
                self.cb_mic['values'] = [f"{i}: {m}" for i,m in enumerate(mics)]
                if mics: self.cb_mic.current(0)
            except: pass
        tk.Button(fm, text="Testar Entrada", command=self.test_in, bg="#2980b9", fg="white").pack(side="left", padx=10)
        
        # Seletor Voz
        fv = tk.LabelFrame(self.f_diag, text="Saída (Voz)", bg="#ecf0f1"); fv.pack(fill="x", pady=5)
        self.cb_voz = ttk.Combobox(fv, state="readonly", width=40); self.cb_voz.pack(side="left", padx=5)
        if TEM_FALA:
            try:
                vs = engine.getProperty('voices')
                self.cb_voz['values'] = [f"{v.id}: {v.name}" for v in vs]
                if vs: self.cb_voz.current(0)
            except: pass
        tk.Button(fv, text="Testar Saída (Fala + Beep)", command=self.test_out, bg="#e67e22", fg="white").pack(side="left", padx=10)
        
        # Log
        tk.Label(self.f_diag, text="Log:", bg="#ecf0f1", font=("bold")).pack(anchor="w", pady=5)
        self.term = tk.Text(self.f_diag, height=10, bg="black", fg="#0F0", font=("Consolas",10)); self.term.pack(fill="both")

    def log_d(self, t): self.term.insert("end", f"\n> {t}"); self.term.see("end")
    def test_out(self):
        if not TEM_FALA: self.log_d("Lib Fala Off"); return
        try:
            if winsound: winsound.Beep(1000, 300) # Tenta beep
            v = self.cb_voz.get()
            if v: 
                idx = self.cb_voz.current()
                global VOZ_ID_SELECIONADA
                VOZ_ID_SELECIONADA = engine.getProperty('voices')[idx].id
                engine.setProperty('voice', VOZ_ID_SELECIONADA)
            self.log_d("Falando...")
            engine.say("Teste de áudio funcionando."); engine.runAndWait()
            self.log_d("OK.")
        except Exception as e: self.log_d(f"Erro: {e}")

    def test_in(self):
        if not TEM_MIC: self.log_d("Lib Mic Off"); return
        sel = self.cb_mic.get()
        midx = int(sel.split(":")[0]) if sel else None
        global MIC_INDEX_SELECIONADO
        MIC_INDEX_SELECIONADO = midx
        self.log_d(f"Ouvindo Mic {midx}... FALE!")
        self.root.update()
        try:
            r = sr.Recognizer()
            with sr.Microphone(device_index=midx) as s:
                r.adjust_for_ambient_noise(s)
                a = r.listen(s, timeout=4)
            t = r.recognize_google(a, language="pt-BR")
            self.log_d(f"Entendi: {t}")
        except Exception as e: self.log_d(f"Erro/Silêncio: {e}")

    # --- ESTATISTICAS ---
    def setup_stats(self):
        nb = ttk.Notebook(self.f_stats); nb.pack(fill="both", expand=True)
        self.tr = tk.Frame(nb); nb.add(self.tr, text="Ranking")
        self.th = tk.Frame(nb); nb.add(self.th, text="Histórico")
        
        cols = ("Nome", "J", "V", "D", "Pts")
        self.tree_r = ttk.Treeview(self.tr, columns=cols, show="headings")
        for c in cols: self.tree_r.heading(c, text=c); self.tree_r.column(c, width=50)
        self.tree_r.pack(fill="both", expand=True)
        
        ch = ("Data", "P1", "Placar", "P2", "Vencedor")
        self.tree_h = ttk.Treeview(self.th, columns=ch, show="headings")
        for c in ch: self.tree_h.heading(c, text=c); self.tree_h.column(c, width=80)
        self.tree_h.pack(fill="both", expand=True)
        tk.Button(self.f_stats, text="Atualizar", command=self.recarregar_estatisticas).pack(pady=5)

    def recarregar_estatisticas(self):
        h = BancoDados.carregar_historico(); j = BancoDados.carregar_jogadores()
        st = {x['nome']:{'j':0,'v':0,'d':0,'p':0} for x in j}
        for x in h:
            p1,p2,v,s1,s2 = x['p1'],x['p2'],x['vencedor'],x['s1'],x['s2']
            if p1 in st: st[p1]['j']+=1; st[p1]['p']+=s1; st[p1]['v' if v==p1 else 'd']+=1
            if p2 in st: st[p2]['j']+=1; st[p2]['p']+=s2; st[p2]['v' if v==p2 else 'd']+=1
        
        for i in self.tree_r.get_children(): self.tree_r.delete(i)
        for n, d in sorted(st.items(), key=lambda x: x[1]['v'], reverse=True):
            self.tree_r.insert("","end", values=(n, d['j'], d['v'], d['d'], d['p']))
            
        for i in self.tree_h.get_children(): self.tree_h.delete(i)
        for x in reversed(h):
            self.tree_h.insert("","end", values=(x['data_hora'], x['p1'], f"{x['s1']}x{x['s2']}", x['p2'], x['vencedor']))

    # --- MODOS ---
    def get_jogs(self):
        cat = self.cb_cat.get(); f=[]
        for j in self.jogadores:
            if cat=="Misto (Todos)" or (cat=="Apenas Masculino" and j['sexo']=="M") or (cat=="Apenas Feminino" and j['sexo']=="F"): f.append(j['nome'])
        if len(f)<2: messagebox.showwarning("Erro", "Min 2 jogs"); return None
        return f

    def abrir_jogo(self, p1, p2, cb, modo):
        if self.janela_aberta: return
        diag = CaixaDialogoVoz(self.root, "Jogo", f"{p1} x {p2}\nIniciar?")
        if diag.resultado:
            self.janela_aberta=True; JanelaPlacarAoVivo(self.root, p1, p2, cb, modo); self.janela_aberta=False
        else: cb(p1, p2, -1, -1)

    def iniciar_mata(self):
        if self.em_torneio: messagebox.showwarning("Erro", "Torneio aberto"); return
        js = self.get_jogs(); 
        if not js: return
        random.shuffle(js)
        self.em_torneio = True
        # Monta arvore simples para visualizacao
        self.arvore_torneio = []; r1 = []
        tmp = js[:]
        bye = tmp.pop() if len(tmp)%2!=0 else None
        for i in range(0,len(tmp),2): r1.append({'p1':tmp[i],'p2':tmp[i+1],'s1':None,'s2':None,'vencedor':None})
        if bye: r1.append({'p1':bye,'p2':None,'vencedor':bye})
        self.arvore_torneio.append(r1)
        q=len(r1)
        while q>1:
            nxt=math.ceil(q/2)
            self.arvore_torneio.append([{'p1':'???','p2':'???','s1':None,'s2':None,'vencedor':None} for _ in range(nxt)])
            q=nxt
        if bye and len(self.arvore_torneio)>1:
            d = self.arvore_torneio[1][(len(r1)-1)//2]
            if d['p1']=='???': d['p1']=bye
            else: d['p2']=bye
        self.viz = VisualizadorChaves(self.root, self.arvore_torneio)
        self.rodada_mata(js, 0)

    def rodada_mata(self, lista, idx):
        if len(lista)==1: 
            self.arvore_torneio[-1]=[{'p1':lista[0],'p2':None,'vencedor':lista[0]}]
            if self.viz: self.viz.atualizar(self.arvore_torneio)
            messagebox.showinfo("Fim", f"Campeão: {lista[0]}"); self.em_torneio=False; return
        
        bye=lista.pop() if len(lista)%2!=0 else None
        pairs = [(lista[i],lista[i+1]) for i in range(0,len(lista),2)]
        wins=[]
        for i, (p1,p2) in enumerate(pairs):
            res={}
            def cb(j1,j2,s1,s2):
                if s1==-1: res['a']=True; return
                w=j1 if s1>s2 else j2; res['w']=w
                m = self.arvore_torneio[idx][i]
                m['s1'], m['s2'], m['vencedor'] = s1, s2, w
            self.abrir_jogo(p1,p2,cb,"Mata")
            if res.get('a'): self.em_torneio=False; return
            if 'w' in res:
                w=res['w']; wins.append(w)
                if idx+1 < len(self.arvore_torneio):
                    d = self.arvore_torneio[idx+1][i//2]
                    if d['p1']=='???': d['p1']=w
                    else: d['p2']=w
                    if self.viz: self.viz.atualizar(self.arvore_torneio)
            else: return
        if bye: 
            wins.append(bye)
            if idx+1 < len(self.arvore_torneio):
                 d = self.arvore_torneio[idx+1][len(pairs)//2]
                 if d['p1']=='???': d['p1']=bye
                 else: d['p2']=bye
                 if self.viz: self.viz.atualizar(self.arvore_torneio)
        self.rodada_mata(wins, idx+1)

    def iniciar_grupo(self):
        if self.em_torneio: messagebox.showwarning("Erro", "Torneio aberto"); return
        js = self.get_jogs(); 
        if not js: return
        self.em_torneio = True
        pts = {p:0 for p in js}
        m = list(itertools.combinations(js,2)); random.shuffle(m)
        for p1,p2 in m:
            res={}
            def cb(j1,j2,s1,s2):
                if s1==-1: res['a']=True; return
                w=j1 if s1>s2 else j2; pts[w]+=3
            self.abrir_jogo(p1,p2,cb,"Grupo")
            if res.get('a'): self.em_torneio=False; return
        import operator
        win = max(pts.items(), key=operator.itemgetter(1))[0]
        messagebox.showinfo("Fim", f"Campeão: {win}"); self.em_torneio=False

    def iniciar_rei(self):
        if self.em_torneio: messagebox.showwarning("Erro", "Torneio aberto"); return
        js = self.get_jogs(); 
        if not js: return
        self.em_torneio = True
        random.shuffle(js)
        r, d, f = js.pop(0), js.pop(0), js
        while True:
            res={}
            def cb(j1,j2,s1,s2):
                if s1==-1: res['a']=True; return
                res['w'] = j1 if s1>s2 else j2; res['l'] = j2 if s1>s2 else j1
            self.abrir_jogo(r,d,cb,"Rei")
            if res.get('a') or 'w' not in res: self.em_torneio=False; break
            w, l = res['w'], res['l']
            if w==r: f.append(l)
            else: f.append(r); r=w
            d = f.pop(0)

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()