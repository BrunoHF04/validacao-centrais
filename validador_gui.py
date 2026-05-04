#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interface gráfica do Validador SIGNO (CEP / CESDI).
Usa CustomTkinter para uma aparência moderna.
"""

import io
import json
import sys
import threading
import tkinter as tk
import tkinter.filedialog as fd
from datetime import datetime
from pathlib import Path

import customtkinter as ctk

# ── Resolução de caminhos compatível com PyInstaller ──────────────────────────
def _base_dir() -> Path:
    """Retorna o diretório raiz — funciona tanto em .py quanto em .exe."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent

BASE_DIR = _base_dir()
sys.path.insert(0, str(BASE_DIR))

# Importa o validador (o mesmo módulo usado pela CLI)
import validador_signo as vs

# ── Tema e paleta ─────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

COR_ERRO    = "#FF5252"
COR_AVISO   = "#FFB300"
COR_OK      = "#4CAF50"
COR_INFO    = "#A0A0A0"
COR_TITULO  = "#C8C8C8"
COR_BG      = "#1A1A1A"
COR_PANEL   = "#222222"
COR_CARD    = "#2C2C2C"
COR_BORDA   = "#E94560"
COR_TEXTO   = "#E0E0E0"
COR_CINZA   = "#666666"


# ─────────────────────────────────────────────────────────────────────────────
# JANELA PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

class ValidadorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Validador SIGNO")
        self.geometry("960x720")
        self.minsize(820, 600)
        self.configure(fg_color=COR_BG)

        # Inicializa tabelas dos manuais em background (silencioso)
        self._tabelas_carregadas = False
        threading.Thread(target=self._carregar_tabelas, daemon=True).start()

        self._arquivo_json: Path | None = None
        self._validando = False

        self._construir_ui()
        self._bind_drag_drop()

    # ── Construção da UI ──────────────────────────────────────────────────────

    def _construir_ui(self):
        # ── Cabeçalho ────────────────────────────────────────────────────────
        cabecalho = ctk.CTkFrame(self, fg_color=COR_CARD, corner_radius=0, height=72)
        cabecalho.pack(fill="x", pady=(0, 0))
        cabecalho.pack_propagate(False)

        ctk.CTkLabel(
            cabecalho,
            text="  ⬡  Validador SIGNO",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=COR_TITULO,
        ).pack(side="left", padx=20, pady=0)

        ctk.CTkLabel(
            cabecalho,
            text="CEP  ·  CESDI  |  Verificação local de JSON",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COR_CINZA,
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            cabecalho,
            text="?",
            command=self._abrir_ajuda,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            width=36,
            height=36,
            corner_radius=18,
            fg_color=COR_CARD,
            hover_color="#3A3A3A",
            border_width=1,
            border_color=COR_INFO,
            text_color=COR_INFO,
        ).pack(side="right", padx=20)

        # ── Corpo ─────────────────────────────────────────────────────────────
        corpo = ctk.CTkFrame(self, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=20, pady=16)
        corpo.columnconfigure(0, weight=0, minsize=280)
        corpo.columnconfigure(1, weight=1)
        corpo.rowconfigure(0, weight=1)

        # ── Painel esquerdo (controles) ───────────────────────────────────────
        self._painel_esquerdo(corpo)

        # ── Painel direito (resultados) ───────────────────────────────────────
        self._painel_resultados(corpo)

        # ── Rodapé ───────────────────────────────────────────────────────────
        self._rodape()

    def _painel_esquerdo(self, pai):
        frame = ctk.CTkFrame(pai, fg_color=COR_PANEL, corner_radius=12)
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        # ── Sistema ──────────────────────────────────────────────────────────
        ctk.CTkLabel(
            frame,
            text="Sistema",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COR_TITULO,
        ).pack(anchor="w", padx=20, pady=(20, 6))

        self._var_sistema = ctk.StringVar(value="CEP")

        for nome in ("CEP", "CESDI"):
            ctk.CTkRadioButton(
                frame,
                text=nome,
                variable=self._var_sistema,
                value=nome,
                font=ctk.CTkFont(size=13),
                fg_color=COR_BORDA,
                hover_color="#C0392B",
            ).pack(anchor="w", padx=24, pady=3)

        # ── Separador ────────────────────────────────────────────────────────
        ctk.CTkFrame(frame, height=1, fg_color=COR_CARD).pack(
            fill="x", padx=16, pady=16
        )

        # ── Arquivo JSON ─────────────────────────────────────────────────────
        ctk.CTkLabel(
            frame,
            text="Arquivo JSON",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COR_TITULO,
        ).pack(anchor="w", padx=20, pady=(0, 8))

        # Zona de drop
        self._zona_drop = ctk.CTkFrame(
            frame,
            fg_color=COR_CARD,
            corner_radius=10,
            height=90,
            border_width=2,
            border_color=COR_CINZA,
        )
        self._zona_drop.pack(fill="x", padx=16, pady=(0, 8))
        self._zona_drop.pack_propagate(False)

        self._lbl_drop = ctk.CTkLabel(
            self._zona_drop,
            text="Arraste o JSON aqui\nou clique em Procurar",
            font=ctk.CTkFont(size=11),
            text_color=COR_CINZA,
            justify="center",
        )
        self._lbl_drop.pack(expand=True)
        self._zona_drop.bind("<Button-1>", lambda e: self._selecionar_arquivo())
        self._lbl_drop.bind("<Button-1>", lambda e: self._selecionar_arquivo())

        ctk.CTkButton(
            frame,
            text="📂  Procurar arquivo...",
            command=self._selecionar_arquivo,
            font=ctk.CTkFont(size=12),
            fg_color=COR_CARD,
            hover_color="#3A3A3A",
            border_width=1,
            border_color=COR_INFO,
            text_color=COR_INFO,
            height=34,
        ).pack(fill="x", padx=16, pady=(0, 4))

        # Nome do arquivo selecionado
        self._lbl_arquivo = ctk.CTkLabel(
            frame,
            text="Nenhum arquivo selecionado",
            font=ctk.CTkFont(size=10),
            text_color=COR_CINZA,
            wraplength=230,
            justify="left",
        )
        self._lbl_arquivo.pack(anchor="w", padx=20, pady=(2, 0))

        # ── Separador ────────────────────────────────────────────────────────
        ctk.CTkFrame(frame, height=1, fg_color=COR_CARD).pack(
            fill="x", padx=16, pady=16
        )

        # ── Botão Validar ────────────────────────────────────────────────────
        self._btn_validar = ctk.CTkButton(
            frame,
            text="▶  VALIDAR",
            command=self._executar_validacao,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=COR_BORDA,
            hover_color="#C0392B",
            height=44,
            corner_radius=10,
        )
        self._btn_validar.pack(fill="x", padx=16)

        # ── Botão Limpar ──────────────────────────────────────────────────────
        ctk.CTkButton(
            frame,
            text="🗑  Limpar",
            command=self._limpar,
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            hover_color=COR_CARD,
            text_color=COR_CINZA,
            height=32,
        ).pack(fill="x", padx=16, pady=(6, 0))

        # ── Status das tabelas ────────────────────────────────────────────────
        ctk.CTkFrame(frame, height=1, fg_color=COR_CARD).pack(
            fill="x", padx=16, pady=16
        )
        self._lbl_status_tab = ctk.CTkLabel(
            frame,
            text="⏳ Carregando manuais...",
            font=ctk.CTkFont(size=10),
            text_color=COR_AVISO,
        )
        self._lbl_status_tab.pack(anchor="w", padx=20)

    def _painel_resultados(self, pai):
        frame = ctk.CTkFrame(pai, fg_color=COR_PANEL, corner_radius=12)
        frame.grid(row=0, column=1, sticky="nsew")

        # Cabeçalho do painel
        top = ctk.CTkFrame(frame, fg_color=COR_CARD, corner_radius=8, height=40)
        top.pack(fill="x", padx=12, pady=(12, 8))
        top.pack_propagate(False)

        ctk.CTkLabel(
            top,
            text="Resultado da Validação",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COR_TITULO,
        ).pack(side="left", padx=12)

        self._lbl_timestamp = ctk.CTkLabel(
            top,
            text="",
            font=ctk.CTkFont(size=10),
            text_color=COR_CINZA,
        )
        self._lbl_timestamp.pack(side="right", padx=12)

        # Área de texto com scrollbar
        self._txt_resultado = tk.Text(
            frame,
            bg="#0D1117",
            fg=COR_TEXTO,
            font=("Consolas", 11),
            relief="flat",
            bd=0,
            padx=14,
            pady=10,
            wrap="word",
            state="disabled",
            selectbackground="#3D3D3D",
            insertbackground=COR_TEXTO,
        )

        scrollbar = ctk.CTkScrollbar(frame, command=self._txt_resultado.yview)
        self._txt_resultado.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y", padx=(0, 8), pady=8)
        self._txt_resultado.pack(fill="both", expand=True, padx=(12, 0), pady=(0, 8))

        # Tags de cor
        self._txt_resultado.tag_configure("erro",   foreground=COR_ERRO,   font=("Consolas", 11, "bold"))
        self._txt_resultado.tag_configure("aviso",  foreground=COR_AVISO)
        self._txt_resultado.tag_configure("ok",     foreground=COR_OK)
        self._txt_resultado.tag_configure("info",   foreground=COR_INFO)
        self._txt_resultado.tag_configure("titulo", foreground=COR_TITULO,  font=("Consolas", 12, "bold"))
        self._txt_resultado.tag_configure("sep",    foreground="#444444")
        self._txt_resultado.tag_configure("cinza",  foreground=COR_CINZA)
        self._txt_resultado.tag_configure("campo",  foreground="#CE9178")
        self._txt_resultado.tag_configure("seta",   foreground=COR_CINZA)
        self._txt_resultado.tag_configure("msg",    foreground="#D4D4D4")

        # Mensagem inicial
        self._escrever_inicial()

        # ── Barra de resumo (rodapé do painel) ───────────────────────────────
        self._barra_resumo = ctk.CTkFrame(frame, fg_color=COR_CARD, corner_radius=8, height=36)
        self._barra_resumo.pack(fill="x", padx=12, pady=(0, 12))
        self._barra_resumo.pack_propagate(False)

        self._lbl_resumo_erros  = ctk.CTkLabel(self._barra_resumo, text="",
                                                font=ctk.CTkFont(size=11, weight="bold"),
                                                text_color=COR_ERRO)
        self._lbl_resumo_avisos = ctk.CTkLabel(self._barra_resumo, text="",
                                                font=ctk.CTkFont(size=11, weight="bold"),
                                                text_color=COR_AVISO)
        self._lbl_resumo_ok     = ctk.CTkLabel(self._barra_resumo, text="",
                                                font=ctk.CTkFont(size=11, weight="bold"),
                                                text_color=COR_OK)
        for w in (self._lbl_resumo_erros, self._lbl_resumo_avisos, self._lbl_resumo_ok):
            w.pack(side="left", padx=16)

    def _abrir_ajuda(self):
        """Abre janela modal com informações sobre o sistema e instruções de uso."""
        if hasattr(self, "_janela_ajuda") and self._janela_ajuda.winfo_exists():
            self._janela_ajuda.focus()
            return

        win = ctk.CTkToplevel(self)
        win.title("Sobre o Validador SIGNO")
        win.geometry("560x620")
        win.resizable(False, False)
        win.configure(fg_color=COR_BG)
        win.transient(self)
        win.grab_set()
        self._janela_ajuda = win

        # Centraliza em relação à janela principal
        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 560) // 2
        y = self.winfo_y() + (self.winfo_height() - 620) // 2
        win.geometry(f"560x620+{x}+{y}")

        # ── Cabeçalho ─────────────────────────────────────────────────────────
        cab = ctk.CTkFrame(win, fg_color=COR_CARD, corner_radius=0, height=64)
        cab.pack(fill="x")
        cab.pack_propagate(False)

        ctk.CTkLabel(
            cab,
            text="⬡  Validador SIGNO",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=COR_TITULO,
        ).pack(side="left", padx=20)

        ctk.CTkLabel(
            cab,
            text="CEP v3.2  •  CESDI v2.5",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COR_CINZA,
        ).pack(side="right", padx=20)

        # ── Conteúdo com scroll ────────────────────────────────────────────────
        scroll = ctk.CTkScrollableFrame(win, fg_color="transparent", corner_radius=0)
        scroll.pack(fill="both", expand=True, padx=24, pady=16)

        def secao(titulo, icone=""):
            ctk.CTkLabel(
                scroll,
                text=f"{icone}  {titulo}" if icone else titulo,
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=COR_TITULO,
                anchor="w",
            ).pack(fill="x", pady=(14, 4))
            ctk.CTkFrame(scroll, height=1, fg_color=COR_CARD).pack(fill="x", pady=(0, 8))

        def paragrafo(texto, cor=None):
            ctk.CTkLabel(
                scroll,
                text=texto,
                font=ctk.CTkFont(size=12),
                text_color=cor or COR_TEXTO,
                anchor="w",
                justify="left",
                wraplength=490,
            ).pack(fill="x", pady=2)

        def item(bullet, texto, cor=None):
            row = ctk.CTkFrame(scroll, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(
                row,
                text=bullet,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=cor or COR_INFO,
                width=22,
                anchor="w",
            ).pack(side="left")
            ctk.CTkLabel(
                row,
                text=texto,
                font=ctk.CTkFont(size=12),
                text_color=COR_TEXTO,
                anchor="w",
                justify="left",
                wraplength=460,
            ).pack(side="left", fill="x", expand=True)

        # ── Sobre ──────────────────────────────────────────────────────────────
        secao("Sobre o sistema", "ℹ")
        paragrafo(
            "O Validador SIGNO é uma ferramenta de diagnóstico local que verifica "
            "arquivos JSON antes do envio às APIs do SIGNO (Sistema de Informações "
            "de Geração de Notas e Operações)."
        )
        paragrafo(
            "A validação é feita inteiramente offline, comparando os campos do JSON "
            "com as regras e valores permitidos definidos nos manuais oficiais."
        )

        # ── Sistemas ──────────────────────────────────────────────────────────
        secao("Sistemas suportados", "⚙")
        item("CEP", "Cadastro de Estrutura de Pagamento — versão 3.2")
        item("CESDI", "Cadastro de Estrutura de Distribuição — versão 2.5")

        # ── Como usar ─────────────────────────────────────────────────────────
        secao("Como usar", "▶")
        item("1.", "Selecione o sistema desejado (CEP ou CESDI) no painel esquerdo.")
        item("2.", "Carregue o arquivo JSON arrastando-o para a zona indicada ou clicando em \"Procurar arquivo...\".")
        item("3.", "Clique em VALIDAR para iniciar o diagnóstico.")
        item("4.", "Analise os resultados no painel direito, com destaque por cores e descrição de cada problema.")

        # ── Legenda de cores ──────────────────────────────────────────────────
        secao("Legenda de cores", "🎨")
        item("[ERRO]",  "Problema crítico — o campo está ausente, inválido ou fora do padrão.", COR_ERRO)
        item("[AVISO]", "Inconsistência ou campo opcional com valor incorreto.", COR_AVISO)
        item("[OK]",    "Campo validado com sucesso.", COR_OK)

        # ── Dicas ─────────────────────────────────────────────────────────────
        secao("Dicas", "💡")
        item("•", "Os manuais são carregados automaticamente ao iniciar o aplicativo.")
        item("•", "Use o botão \"Limpar\" para reiniciar a validação com um novo arquivo.")
        item("•", "O diagnóstico não altera nem envia o arquivo — é apenas leitura local.")

        # ── Botão fechar ───────────────────────────────────────────────────────
        ctk.CTkButton(
            win,
            text="Fechar",
            command=win.destroy,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COR_BORDA,
            hover_color="#C0392B",
            height=40,
            corner_radius=10,
        ).pack(fill="x", padx=24, pady=(0, 20))

    def _rodape(self):
        rod = ctk.CTkFrame(self, fg_color=COR_CARD, corner_radius=0, height=28)
        rod.pack(fill="x", side="bottom")
        rod.pack_propagate(False)
        ctk.CTkLabel(
            rod,
            text="Validador SIGNO  •  CEP v3.2  •  CESDI v2.5",
            font=ctk.CTkFont(size=10),
            text_color=COR_CINZA,
        ).pack(side="left", padx=16)

    # ── Drag & Drop ───────────────────────────────────────────────────────────

    def _bind_drag_drop(self):
        """Tenta ativar drag-and-drop nativo (TkinterDnD2), ignora se indisponível."""
        try:
            from tkinterdnd2 import DND_FILES, TkinterDnD  # noqa
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<Drop>>", self._on_drop)
            self._zona_drop.drop_target_register(DND_FILES)
            self._zona_drop.dnd_bind("<<Drop>>", self._on_drop)
        except Exception:
            pass

    def _on_drop(self, event):
        caminho = event.data.strip().strip("{}")
        self._definir_arquivo(Path(caminho))

    # ── Ações ─────────────────────────────────────────────────────────────────

    def _selecionar_arquivo(self):
        caminho = fd.askopenfilename(
            title="Selecionar arquivo JSON",
            filetypes=[("JSON", "*.json"), ("Todos os arquivos", "*.*")],
        )
        if caminho:
            self._definir_arquivo(Path(caminho))

    def _definir_arquivo(self, caminho: Path):
        self._arquivo_json = caminho
        nome = caminho.name
        self._lbl_arquivo.configure(text=nome, text_color=COR_INFO)
        self._lbl_drop.configure(
            text=f"✔  {nome}",
            text_color=COR_OK,
            font=ctk.CTkFont(size=10, weight="bold"),
        )
        self._zona_drop.configure(border_color=COR_OK)

    def _limpar(self):
        self._arquivo_json = None
        self._lbl_arquivo.configure(text="Nenhum arquivo selecionado", text_color=COR_CINZA)
        self._lbl_drop.configure(
            text="Arraste o JSON aqui\nou clique em Procurar",
            text_color=COR_CINZA,
            font=ctk.CTkFont(size=11),
        )
        self._zona_drop.configure(border_color=COR_CINZA)
        self._lbl_resumo_erros.configure(text="")
        self._lbl_resumo_avisos.configure(text="")
        self._lbl_resumo_ok.configure(text="")
        self._lbl_timestamp.configure(text="")
        self._txt_resultado.configure(state="normal")
        self._txt_resultado.delete("1.0", "end")
        self._escrever_inicial()
        self._txt_resultado.configure(state="disabled")

    def _executar_validacao(self):
        if self._validando:
            return
        if not self._arquivo_json or not self._arquivo_json.exists():
            self._mostrar_erro_inline("Selecione um arquivo JSON válido antes de validar.")
            return
        if not self._tabelas_carregadas:
            self._mostrar_erro_inline("Aguarde — os manuais ainda estão sendo carregados...")
            return

        self._validando = True
        self._btn_validar.configure(text="⏳  Validando...", state="disabled")
        threading.Thread(target=self._validar_em_thread, daemon=True).start()

    def _validar_em_thread(self):
        """Roda a validação em thread separada para não travar a UI."""
        try:
            with open(self._arquivo_json, encoding="utf-8") as f:
                dados = json.load(f)
        except json.JSONDecodeError as e:
            self.after(0, self._exibir_erro_json, str(e))
            return
        except Exception as e:
            self.after(0, self._exibir_erro_json, str(e))
            return

        sistema = self._var_sistema.get()
        rel = vs.Relatorio(sistema=sistema, arquivo=str(self._arquivo_json))

        if sistema == "CEP":
            vs.validar_cep_json(dados, rel)
        else:
            vs.validar_cesdi_json(dados, rel)

        self.after(0, self._exibir_relatorio, rel)

    # ── Exibição dos resultados ───────────────────────────────────────────────

    def _escrever_inicial(self):
        self._append("titulo", "  Validador SIGNO\n")
        self._append("cinza",  "  Selecione o sistema (CEP ou CESDI), escolha um arquivo JSON\n")
        self._append("cinza",  "  e clique em VALIDAR para ver o diagnóstico detalhado.\n\n")
        self._append("sep",    "  " + "─" * 58 + "\n\n")
        self._append("cinza",  "  Os resultados aparecerão aqui com destaque por cores:\n\n")
        self._append("erro",   "  [ERRO]   Campo com problema crítico\n")
        self._append("aviso",  "  [AVISO]  Inconsistência ou campo opcional incorreto\n")
        self._append("ok",     "  [OK]     Campo validado com sucesso\n")

    def _exibir_relatorio(self, rel: vs.Relatorio):
        self._txt_resultado.configure(state="normal")
        self._txt_resultado.delete("1.0", "end")

        ts = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self._lbl_timestamp.configure(text=ts)

        # Cabeçalho
        self._append("sep",    "  " + "═" * 58 + "\n")
        self._append("titulo", f"  Sistema: {rel.sistema}   |   {Path(rel.arquivo).name}\n")
        self._append("sep",    "  " + "═" * 58 + "\n\n")

        if not rel.erros and not rel.avisos:
            self._append("ok", "  ✔  JSON VÁLIDO — Nenhum problema encontrado!\n\n")
        else:
            # Erros
            if rel.erros:
                self._append("erro", f"  ERROS CRÍTICOS ({len(rel.erros)})\n")
                self._append("sep",  "  " + "─" * 56 + "\n")
                for campo, msg in rel.erros:
                    self._append("erro",  "  [ERRO]  ")
                    self._append("campo", f"{campo}\n")
                    for linha in msg.split("\n"):
                        self._append("seta", "          → ")
                        self._append("msg",  linha.strip() + "\n")
                    self._append("msg", "\n")

            # Avisos
            if rel.avisos:
                self._append("aviso", f"  AVISOS / INCONSISTÊNCIAS ({len(rel.avisos)})\n")
                self._append("sep",   "  " + "─" * 56 + "\n")
                for campo, msg in rel.avisos:
                    self._append("aviso", "  [AVISO] ")
                    self._append("campo", f"{campo}\n")
                    for linha in msg.split("\n"):
                        self._append("seta", "          → ")
                        self._append("msg",  linha.strip() + "\n")
                    self._append("msg", "\n")

        # Resumo
        self._append("sep", "  " + "═" * 58 + "\n")
        self._append("cinza", "  RESUMO:  ")
        self._append("erro",  f"{len(rel.erros)} erro(s)   ")
        self._append("aviso", f"{len(rel.avisos)} aviso(s)   ")
        self._append("ok",    f"{len(rel.ok)} campo(s) OK\n")
        self._append("sep", "  " + "═" * 58 + "\n")

        self._txt_resultado.configure(state="disabled")
        self._txt_resultado.see("1.0")

        # Barra de resumo
        icone_e = "✘" if rel.erros else "✔"
        icone_a = "⚠" if rel.avisos else "✔"
        self._lbl_resumo_erros.configure(text=f"  {icone_e}  {len(rel.erros)} erro(s)")
        self._lbl_resumo_avisos.configure(text=f"  {icone_a}  {len(rel.avisos)} aviso(s)")
        self._lbl_resumo_ok.configure(text=f"  ✔  {len(rel.ok)} campo(s) OK")

        self._btn_validar.configure(text="▶  VALIDAR", state="normal")
        self._validando = False

    def _exibir_erro_json(self, mensagem: str):
        self._txt_resultado.configure(state="normal")
        self._txt_resultado.delete("1.0", "end")
        self._append("erro",  "  [ERRO FATAL] JSON com sintaxe inválida\n\n")
        self._append("msg",   f"  {mensagem}\n\n")
        self._append("cinza", "  Verifique se o arquivo é um JSON válido e tente novamente.\n")
        self._txt_resultado.configure(state="disabled")
        self._btn_validar.configure(text="▶  VALIDAR", state="normal")
        self._validando = False

    def _mostrar_erro_inline(self, msg: str):
        self._txt_resultado.configure(state="normal")
        self._txt_resultado.delete("1.0", "end")
        self._append("aviso", f"\n  ⚠  {msg}\n")
        self._txt_resultado.configure(state="disabled")

    def _append(self, tag: str, texto: str):
        self._txt_resultado.insert("end", texto, tag)

    # ── Carregamento das tabelas ──────────────────────────────────────────────

    def _carregar_tabelas(self):
        # Redireciona prints do módulo validador para silêncio durante load
        _stdout_bkp = sys.stdout
        sys.stdout = io.StringIO()
        try:
            # Sobrescreve o BASE_DIR do módulo para apontar ao diretório correto
            vs.BASE_DIR = BASE_DIR
            vs.MANUAIS_CEP_DIR   = BASE_DIR / "manuais" / "CEP"
            vs.MANUAIS_CESDI_DIR = BASE_DIR / "manuais" / "CESDI"
            vs.inicializar_tabelas()
            self._tabelas_carregadas = True
            self.after(0, self._on_tabelas_ok)
        except Exception as e:
            self.after(0, self._on_tabelas_erro, str(e))
        finally:
            sys.stdout = _stdout_bkp

    def _on_tabelas_ok(self):
        self._lbl_status_tab.configure(
            text="✔ Manuais carregados com sucesso",
            text_color=COR_OK,
        )

    def _on_tabelas_erro(self, msg: str):
        self._lbl_status_tab.configure(
            text=f"⚠ Erro ao carregar manuais",
            text_color=COR_AVISO,
        )


# ─────────────────────────────────────────────────────────────────────────────
# ENTRADA
# ─────────────────────────────────────────────────────────────────────────────

def main():
    app = ValidadorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
