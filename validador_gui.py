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
import tkinter.ttk as ttk
from datetime import datetime
from pathlib import Path

import re as _re
import customtkinter as ctk


# ─────────────────────────────────────────────────────────────────────────────
# EXTRAÇÃO DE ATOS DE ARQUIVO DE LOG
# ─────────────────────────────────────────────────────────────────────────────

def _extrair_atos_do_log(caminho_log: Path) -> list:
    """Lê um .log do Orion/Signo e devolve lista de JSONs únicos de atos."""
    vistos: dict = {}
    with open(caminho_log, encoding="utf-8", errors="replace") as f:
        for linha in f:
            if "JSON ENTRADA >>" not in linha:
                continue
            idx = linha.index("JSON ENTRADA >>") + len("JSON ENTRADA >>")
            rest = linha[idx:].strip()
            saida_idx = rest.find(" JSON SAIDA >>")
            if saida_idx > 0:
                rest = rest[:saida_idx]
            try:
                outer = json.loads(rest)
                entrada_str = outer.get("jsonEntrada", "")
                sistema = outer.get("tipoComunicacaoSigno", "CEP")
                if not entrada_str or entrada_str in vistos:
                    continue
                dados = json.loads(entrada_str)
                dados["_sistema_log"] = sistema
                vistos[entrada_str] = dados
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
    return list(vistos.values())


def _label_ato(ato: dict) -> str:
    """Retorna texto de identificação de um ato: 'Livro X  Fl. Y–Z'."""
    liv_i = ato.get("livroInicial", "?")
    liv_f = ato.get("livroFinal", "?")
    fl_i  = ato.get("folhaInicial", "?")
    fl_f  = ato.get("folhaFinal", "?")
    livro = f"Livro {liv_i}" if liv_i == liv_f else f"Livros {liv_i}–{liv_f}"
    folha = f"Fl. {fl_i}" if fl_i == fl_f else f"Fl. {fl_i}–{fl_f}"
    return f"{livro}   {folha}"

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
ctk.set_default_color_theme("blue")

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
# TRADUÇÃO DE CAMPOS E MENSAGENS (linguagem amigável ao usuário)
# ─────────────────────────────────────────────────────────────────────────────

_CAMPOS = {
    # Campos raiz — CEP e CESDI
    "tipoAto":                          "Tipo do Ato",
    "naturezaAto":                      "Natureza do Ato",
    "status":                           "Status",
    "statusAto":                        "Status do Ato",
    "livroInicial":                     "Livro Inicial",
    "livroFinal":                       "Livro Final",
    "folhaInicial":                     "Folha Inicial",
    "folhaFinal":                       "Folha Final",
    "dataAto":                          "Data do Ato",
    "dataContrato":                     "Data do Contrato",
    "dataInclusao":                     "Data de Inclusão",
    "dataCasamento":                    "Data do Casamento",
    "reservaDePoderes":                 "Reserva de Poderes",
    "valorOperacao":                    "Valor da Operação",
    "prazoPagamento":                   "Prazo de Pagamento",
    "formaPagamento":                   "Forma de Pagamento",
    "existeBemEdireito":                "Existência de Bem/Direito",
    "existeBemEdireitoVinculadoAoAto":  "Existência de Bem/Direito Vinculado ao Ato",
    "naturezaLitigio":                  "Natureza do Litígio",
    "acordo":                           "Acordo",
    "tipoInvalidacaoAto":               "Tipo de Invalidação do Ato",
    "tipoAtoOrigem":                    "Tipo do Ato de Origem",
    "municipioCartorioAtoOrigem":       "Município do Cartório de Origem",
    "cartorioAtual":                    "Cartório Atual",
    "cartorioNaoCadastrado":            "Cartório Não Cadastrado",
    "regimeDeBensDireitosDoCasamento":  "Regime de Bens do Casamento",
    "quantidadefilhosMaiores":          "Quantidade de Filhos Maiores",
    "quantidadefilhosMenores":          "Quantidade de Filhos Menores",
    "partes":                           "Lista de Partes",
    "bensEdireitos":                    "Bens e Direitos",
    "atosOrigem":                       "Atos de Origem",
    "anexos":                           "Anexos",
    "anexosEspecificos":                "Anexos Específicos",
    "attachments":                      "Anexos",
    # Campos de parte
    "qualificacaoParte":    "Qualificação da Parte",
    "nomeParte":            "Nome da Parte",
    "cpf":                  "CPF/CNPJ",
    "cpfConjuge":           "CPF do Cônjuge",
    "cep":                  "CEP",
    "cepResidencia":        "CEP de Residência",
    "dataNascimento":       "Data de Nascimento",
    "dataNascimentoParte":  "Data de Nascimento",
    "dataEmissao":          "Data de Emissão do Documento",
    "dataEmissaoDocumento": "Data de Emissão do Documento",
    "dataObito":            "Data de Óbito",
    "estadoCivil":          "Estado Civil",
    "estadoCivilParte":     "Estado Civil",
    "genero":               "Gênero",
    "tipoDocumento":        "Tipo de Documento",
    "tipoContato":          "Tipo de Contato",
    "tipoContatoParte":     "Tipo de Contato",
    "capacidadeCivil":      "Capacidade Civil",
    "areaAtuacao":          "Área de Atuação",
    "profissao":            "Profissão",
    "regimeBens":           "Regime de Bens",
    "municipio":            "Município",
    "cidadeResidencia":     "Cidade de Residência",
    "nacionalidade":        "Nacionalidade",
    "nacionalidadeParte":   "Nacionalidade",
    "paisOrigem":           "País de Origem",
    "codigoPaisParte":      "Código do País",
    "codigoPaisResidencia": "Código do País de Residência",
    "semFiliacoes":         "Sem Filiações",
    "naoPossuiFiliacao":    "Sem Filiação",
    "responsavelFilhosMenores": "Responsável por Filhos Menores",
    "filiacoes":            "Filiações",
    # Campos de bem/direito
    "qualificacaodeBens":           "Tipo do Bem/Direito",
    "tipoBemEdireito":              "Tipo do Bem/Direito",
    "referenciaCadastralImovel":    "Referência Cadastral do Imóvel",
    "cin":                          "CIN (Código Imobiliário Nacional)",
    "valor":                        "Valor",
    "valorFiscal":                  "Valor Fiscal",
    "valorImovel":                  "Valor do Imóvel",
    "valorDoBem":                   "Valor do Bem",
    "quantidadeAreaConstruida":     "Área Construída",
    "quantidadeAreaTotal":          "Área Total",
    "quantidadeUnidadeAreaConstruida": "Área Construída",
    "titulares":                    "Titulares",
    # Campos de ato de origem
    "cartorio":                     "CNS do Cartório de Origem",
    "numeroCns":                    "Número do CNS",
    "atosAnteriores":               "Atos Anteriores",
    "outroCartorio":                "Outro Cartório",
    "tribunal":                     "Tribunal",
    # Campos CESDI específicos de parte
    "areaAtuacaoParte":             "Área de Atuação",
    "profissaoParte":               "Profissão",
    # Campos de anexo
    "base64Content":    "Conteúdo do Arquivo (base64)",
    "extensaoArquivo":  "Extensão do Arquivo",
    "nome":             "Nome do Arquivo",
}


def _traduzir_campo(campo: str) -> str:
    """Converte nome técnico do campo para linguagem amigável."""
    # Tenta correspondência exata primeiro
    if campo in _CAMPOS:
        return _CAMPOS[campo]

    # Padrões com índice: partes[0].nomeParte, bensEdireitos[1].cin, etc.
    m = _re.match(r"^(\w+)\[(\d+)\]\.(.+)$", campo)
    if m:
        pai, idx, filho = m.group(1), int(m.group(2)) + 1, m.group(3)
        nome_pai = {
            "partes":           "Parte",
            "bensEdireitos":    "Bem/Direito",
            "atosOrigem":       "Ato de Origem",
            "attachments":      "Anexo",
            "anexos":           "Anexo",
            "anexosEspecificos":"Anexo Específico",
        }.get(pai, pai)

        # Filho pode ser aninhado: titulares[0].cpf
        m2 = _re.match(r"^(\w+)\[(\d+)\]\.(.+)$", filho)
        if m2:
            sub_pai, sub_idx, sub_filho = m2.group(1), int(m2.group(2)) + 1, m2.group(3)
            nome_sub = _CAMPOS.get(sub_filho, sub_filho)
            return f"{nome_sub} — {_CAMPOS.get(sub_pai, sub_pai)} {sub_idx} do {nome_pai} {idx}"

        nome_filho = _CAMPOS.get(filho, filho)
        return f"{nome_filho} — {nome_pai} {idx}"

    # Padrão lista sem filho: partes[0]
    m = _re.match(r"^(\w+)\[(\d+)\]$", campo)
    if m:
        pai, idx = m.group(1), int(m.group(2)) + 1
        nome_pai = _CAMPOS.get(pai, pai)
        return f"{nome_pai} {idx}"

    return campo


def _traduzir_mensagem(msg: str) -> str:
    """Converte mensagem técnica de validação para linguagem amigável."""
    msg = msg.strip()

    # Campos obrigatórios ausentes
    if msg in (
        "Campo inteiro obrigatório não informado.",
        "Campo obrigatório não informado.",
        "Campo string obrigatório está ausente ou vazio.",
    ):
        return "Campo obrigatório não preenchido."

    # Código inválido com tabela de válidos
    m = _re.match(r"Código (\S+) não reconhecido na tabela '(.+?)'\.(.+)", msg, _re.DOTALL)
    if m:
        codigo, tabela, resto = m.group(1), m.group(2), m.group(3)
        # Extrai a lista de códigos válidos
        m2 = _re.search(r"Códigos válidos:\s*(.+)", resto, _re.DOTALL)
        lista = m2.group(1).strip() if m2 else ""
        return (
            f"O código '{codigo}' não é válido para este campo.\n"
            f"Códigos aceitos: {lista}"
        )

    # Formato de data inválido
    if "Formato de data inválido" in msg or "ISO 8601" in msg:
        return "Data em formato inválido. Use o padrão AAAA-MM-DD (ex: 2024-06-01)."

    # Tipo inválido — esperado inteiro
    if "esperado inteiro" in msg.lower() or "esperado número" in msg.lower():
        m = _re.search(r"recebid[oa]\s+(\w+)[:\s]+(.+)", msg)
        val = f" Valor recebido: {m.group(2).strip()!r}" if m else ""
        return f"O valor informado deve ser um número inteiro.{val}"

    # Esperado string (CPF, CNPJ, CEP, CNS)
    if "preservar zeros à esquerda" in msg or ("deve ser string" in msg and "preservar" in msg):
        return (
            "Este campo deve ser preenchido como texto (entre aspas), "
            "não como número, para preservar os zeros à esquerda (ex: \"01234567\")."
        )
    if "deve ser string" in msg.lower():
        return "Este campo deve ser preenchido como texto (string)."

    # Tipo inválido genérico
    if "tipo inválido" in msg.lower():
        m = _re.search(r"recebid[oa]\s+(\w+)[:\s]+(.+)", msg, _re.IGNORECASE)
        val = f" Recebido: {m.group(2).strip()}" if m else ""
        return f"Tipo de dado incorreto.{val} Verifique o valor informado."

    # Deve ser string com tamanho errado (CEP, CPF, etc.)
    m = _re.match(r"(.+) tem (\d+) dígito\(s\); esperado (\d+)\. Valor: (.+)", msg)
    if m:
        nome, qtd, esp, val = m.group(1), m.group(2), m.group(3), m.group(4)
        return f"{nome} inválido: informado com {qtd} dígito(s), mas deve ter {esp}. Valor: {val}"

    # Esperado booleano
    if "esperado booleano" in msg.lower():
        m = _re.search(r"recebid[oa]:\s*(.+)", msg, _re.IGNORECASE)
        val = f" Valor recebido: {m.group(1).strip()}" if m else ""
        return f"Este campo deve ser verdadeiro (true) ou falso (false).{val}"

    # Esperado string com tipo recebido
    if "esperado string" in msg.lower():
        m = _re.search(r"recebid[oa]\s+(\w+)[:\s]+(.+)", msg, _re.IGNORECASE)
        val = f" Recebido: {m.group(2).strip()}" if m else ""
        return f"O valor deve ser um texto (string).{val}"

    # Campo de lista inválido
    if "deve ser uma lista" in msg:
        return "Este campo deve ser uma lista de itens."

    # Nenhuma parte informada
    if "nenhuma parte informada" in msg.lower():
        return "Nenhuma parte foi informada no ato. Adicione ao menos uma parte."

    # Campo de anexo ausente
    if "campo de anexo vazio ou ausente" in msg.lower():
        return "Campo obrigatório do anexo não preenchido."

    # Fallback: retorna mensagem original sem alteração
    return msg


# ─────────────────────────────────────────────────────────────────────────────
# JANELA PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

class ValidadorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Validador SIGNO")
        self.geometry("960x860")
        self.minsize(820, 700)
        self.configure(fg_color=COR_BG)

        # Inicializa tabelas dos manuais em background (silencioso)
        self._tabelas_carregadas = False
        threading.Thread(target=self._carregar_tabelas, daemon=True).start()

        self._arquivo_json: Path | None = None
        self._validando = False
        self._dados_atuais: dict | None = None
        self._tree_paths: dict = {}
        self._modo_estrutura: str = "graph"
        self._zoom: float = 1.0

        # ── Estado do modo log ────────────────────────────────────────────────
        self._atos_log: list = []
        self._arquivo_log: Path | None = None
        self._dados_log_ato: dict | None = None
        self._btn_atos: list = []

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

        # Zona de drop (invisível, mantida para drag-and-drop funcionar)
        self._zona_drop = ctk.CTkFrame(
            frame,
            fg_color="transparent",
            corner_radius=0,
            height=0,
            border_width=0,
        )
        self._zona_drop.pack(fill="x", padx=16)
        self._zona_drop.pack_propagate(False)

        self._lbl_drop = ctk.CTkLabel(
            self._zona_drop,
            text="",
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
            fill="x", padx=16, pady=(16, 8)
        )

        # ── Arquivo de Log ────────────────────────────────────────────────────
        ctk.CTkLabel(
            frame,
            text="Arquivo de Log",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COR_TITULO,
        ).pack(anchor="w", padx=20, pady=(0, 6))

        ctk.CTkButton(
            frame,
            text="📋  Importar Log...",
            command=self._importar_log,
            font=ctk.CTkFont(size=12),
            fg_color=COR_CARD,
            hover_color="#3A3A3A",
            border_width=1,
            border_color=COR_INFO,
            text_color=COR_INFO,
            height=34,
        ).pack(fill="x", padx=16, pady=(0, 4))

        self._lbl_log = ctk.CTkLabel(
            frame,
            text="Nenhum log carregado",
            font=ctk.CTkFont(size=10),
            text_color=COR_CINZA,
            wraplength=230,
            justify="left",
        )
        self._lbl_log.pack(anchor="w", padx=20, pady=(0, 4))

        self._frame_lista_atos = ctk.CTkScrollableFrame(
            frame,
            fg_color=COR_CARD,
            corner_radius=8,
            height=0,
            scrollbar_button_color=COR_CINZA,
            scrollbar_button_hover_color=COR_INFO,
        )
        self._frame_lista_atos.pack(fill="x", padx=16, pady=(0, 4))

        # ── Separador ────────────────────────────────────────────────────────
        ctk.CTkFrame(frame, height=1, fg_color=COR_CARD).pack(
            fill="x", padx=16, pady=(8, 16)
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
        top.pack(fill="x", padx=12, pady=(12, 4))
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

        # ── Abas Simplificado / Técnico ───────────────────────────────────────
        abas = ctk.CTkTabview(
            frame,
            fg_color="#0D1117",
            segmented_button_fg_color=COR_CARD,
            segmented_button_selected_color=COR_BORDA,
            segmented_button_selected_hover_color="#C0392B",
            segmented_button_unselected_color=COR_CARD,
            segmented_button_unselected_hover_color="#3A3A3A",
            text_color=COR_TEXTO,
            text_color_disabled=COR_CINZA,
            corner_radius=8,
        )
        abas.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        abas.add("Simplificado")
        abas.add("Técnico")
        abas.add("Estrutura")

        self._txt_resultado  = self._criar_area_texto(abas.tab("Simplificado"))
        self._txt_tecnico    = self._criar_area_texto(abas.tab("Técnico"))
        self._criar_tree_view(abas.tab("Estrutura"))

        # Mensagem inicial em ambas as abas
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

    def _criar_area_texto(self, container) -> tk.Text:
        """Cria uma área de texto com scrollbar dentro do container dado."""
        wrapper = ctk.CTkFrame(container, fg_color="transparent")
        wrapper.pack(fill="both", expand=True)

        txt = tk.Text(
            wrapper,
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
        sb = ctk.CTkScrollbar(wrapper, command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y", padx=(0, 4), pady=4)
        txt.pack(side="left", fill="both", expand=True, pady=4)

        txt.tag_configure("erro",   foreground=COR_ERRO,   font=("Consolas", 11, "bold"))
        txt.tag_configure("aviso",  foreground=COR_AVISO)
        txt.tag_configure("ok",     foreground=COR_OK)
        txt.tag_configure("info",   foreground=COR_INFO)
        txt.tag_configure("titulo", foreground=COR_TITULO,  font=("Consolas", 12, "bold"))
        txt.tag_configure("sep",    foreground="#444444")
        txt.tag_configure("cinza",  foreground=COR_CINZA)
        txt.tag_configure("campo",  foreground="#CE9178")
        txt.tag_configure("seta",   foreground=COR_CINZA)
        txt.tag_configure("msg",    foreground="#D4D4D4")
        return txt

    # ── Aba Estrutura (Graph canvas — estilo JSON Crack) ──────────────────────

    _CARD_W   = 230   # largura de cada card
    _CARD_MH  = 26    # altura do cabeçalho do card
    _ROW_H    = 20    # altura de cada linha de campo
    _COL_GAP  = 60    # espaço horizontal entre colunas
    _ROW_GAP  = 10    # espaço vertical entre cards irmãos

    def _criar_tree_view(self, parent):
        # ── Barra de toggle Graph / Tree ─────────────────────────────────────
        barra = tk.Frame(parent, bg=COR_CARD, height=34)
        barra.pack(fill="x")
        barra.pack_propagate(False)

        self._btn_modo_graph = ctk.CTkButton(
            barra, text="⬡  Graph", width=90, height=26,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=COR_BORDA, hover_color="#C0392B", text_color="white",
            corner_radius=6, command=lambda: self._trocar_modo_estrutura("graph"),
        )
        self._btn_modo_graph.pack(side="left", padx=(8, 4), pady=4)

        self._btn_modo_tree = ctk.CTkButton(
            barra, text="≡  Tree", width=80, height=26,
            font=ctk.CTkFont(size=11),
            fg_color=COR_CARD, hover_color="#3A3A3A", text_color=COR_CINZA,
            border_width=1, border_color=COR_CINZA, corner_radius=6,
            command=lambda: self._trocar_modo_estrutura("tree"),
        )
        self._btn_modo_tree.pack(side="left", padx=4, pady=4)

        # ── Frame do Graph (canvas) ───────────────────────────────────────────
        self._frame_graph = tk.Frame(parent, bg="#0D1117")
        self._frame_graph.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(self._frame_graph, bg="#0D1117", highlightthickness=0)
        vsb_g = tk.Scrollbar(self._frame_graph, orient="vertical",   command=self._canvas.yview)
        hsb_g = tk.Scrollbar(self._frame_graph, orient="horizontal", command=self._canvas.xview)
        self._canvas.configure(yscrollcommand=vsb_g.set, xscrollcommand=hsb_g.set)
        vsb_g.pack(side="right",  fill="y")
        hsb_g.pack(side="bottom", fill="x")

        # ── Barra de zoom (flutuante no rodapé do canvas) ─────────────────────
        zoom_bar = tk.Frame(self._frame_graph, bg="#21262D", pady=4)
        zoom_bar.pack(side="bottom", fill="x")

        _zb = dict(height=28, corner_radius=6,
                   fg_color="#30363D", hover_color="#3D444D", text_color="#C8C8C8")
        ctk.CTkButton(zoom_bar, text="−", width=38,
                      font=ctk.CTkFont(size=15), command=self._zoom_out,
                      **_zb).pack(side="left", padx=(8, 2), pady=2)
        ctk.CTkButton(zoom_bar, text="+", width=38,
                      font=ctk.CTkFont(size=15), command=self._zoom_in,
                      **_zb).pack(side="left", padx=2, pady=2)

        self._lbl_zoom = ctk.CTkLabel(zoom_bar, text="100%",
                                      font=ctk.CTkFont(size=11),
                                      text_color="#888888", width=42)
        self._lbl_zoom.pack(side="left", padx=4)

        ctk.CTkButton(zoom_bar, text="⊡", width=38,
                      font=ctk.CTkFont(size=14), command=self._zoom_fit,
                      **_zb).pack(side="left", padx=(8, 2), pady=2)
        ctk.CTkButton(zoom_bar, text="1:1", width=44,
                      font=ctk.CTkFont(size=11), command=self._zoom_reset,
                      **_zb).pack(side="left", padx=2, pady=2)

        self._canvas.pack(fill="both", expand=True)
        self._canvas.bind("<MouseWheel>",
            lambda e: self._canvas.yview_scroll(-1 if e.delta > 0 else 1, "units"))
        self._canvas.bind("<Shift-MouseWheel>",
            lambda e: self._canvas.xview_scroll(-1 if e.delta > 0 else 1, "units"))
        self._canvas.bind("<Control-MouseWheel>",
            lambda e: self._zoom_in() if e.delta > 0 else self._zoom_out())

        # ── Frame do Tree (treeview ttk) ──────────────────────────────────────
        self._frame_tree = tk.Frame(parent, bg=COR_BG)

        style = ttk.Style()
        try:
            style.theme_use("default")
        except Exception:
            pass
        style.configure("Json.Treeview",
            background="#161B22", foreground=COR_TEXTO,
            fieldbackground="#161B22", borderwidth=0,
            rowheight=22, font=("Consolas", 10),
        )
        style.configure("Json.Treeview.Heading",
            background=COR_CARD, foreground=COR_TITULO,
            relief="flat", font=("Consolas", 10, "bold"),
        )
        style.map("Json.Treeview",
            background=[("selected", "#3A3A3A")],
            foreground=[("selected", COR_BORDA)],
        )

        self._treeview = ttk.Treeview(
            self._frame_tree, style="Json.Treeview",
            show="tree headings", columns=("valor",), selectmode="browse",
        )
        self._treeview.heading("#0",     text="Campo", anchor="w")
        self._treeview.heading("valor",  text="Valor", anchor="w")
        self._treeview.column("#0",    width=220, minwidth=80, stretch=True)
        self._treeview.column("valor", width=340, minwidth=80, stretch=True)

        for tag, fg, font in [
            ("str",      "#CE9178", ("Consolas", 10)),
            ("num",      "#B5CEA8", ("Consolas", 10)),
            ("bool",     "#569CD6", ("Consolas", 10)),
            ("null",     "#808080", ("Consolas", 10)),
            ("obj",      COR_AVISO, ("Consolas", 10)),
            ("arr",      COR_AVISO, ("Consolas", 10)),
            ("erro",     COR_ERRO,  ("Consolas", 10, "bold")),
            ("erro_pai", "#FF8A80", ("Consolas", 10)),
            ("aviso",    COR_AVISO, ("Consolas", 10, "bold")),
            ("av_pai",   "#FFD180", ("Consolas", 10)),
        ]:
            self._treeview.tag_configure(tag, foreground=fg, font=font)

        vsb_t = tk.Scrollbar(self._frame_tree, orient="vertical",   command=self._treeview.yview)
        hsb_t = tk.Scrollbar(self._frame_tree, orient="horizontal", command=self._treeview.xview)
        self._treeview.configure(yscrollcommand=vsb_t.set, xscrollcommand=hsb_t.set)
        vsb_t.pack(side="right",  fill="y")
        hsb_t.pack(side="bottom", fill="x")
        self._treeview.pack(fill="both", expand=True)

    def _popular_tree(self, dados: dict | None,
                      campos_erro: set | None = None,
                      campos_aviso: set | None = None):
        if not hasattr(self, "_canvas"):
            return
        ce = campos_erro  or set()
        ca = campos_aviso or set()
        self._last_campos_erro  = ce
        self._last_campos_aviso = ca

        if self._modo_estrutura == "graph":
            self._canvas.delete("all")
            if not dados:
                return
            dados_limpos = {k: v for k, v in dados.items() if not str(k).startswith("_")}
            root = self._build_json_card("raiz", dados_limpos, "")
            self._layout_card(root, 16, 16)
            self._draw_connections(root)
            self._draw_json_graph(root, ce, ca)
            self._canvas.update_idletasks()
            self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        else:
            if not dados:
                self._treeview.delete(*self._treeview.get_children())
                return
            self._popular_treeview(dados, ce, ca)

    # ── Construção dos cards ──────────────────────────────────────────────────

    def _build_json_card(self, key, value, path: str) -> dict:
        card = {"title": str(key), "path": path,
                "fields": [], "children": [], "x": 0, "y": 0, "h": 0, "sh": 0}
        if isinstance(value, dict):
            items = [(k, v) for k, v in value.items() if not str(k).startswith("_")]
        elif isinstance(value, list):
            items = list(enumerate(value))
        else:
            items = []

        for k, v in items:
            if isinstance(k, int):
                child_path = f"{path}[{k}]"
            else:
                child_path = f"{path}.{k}" if path else str(k)

            if isinstance(v, dict) and v:
                child = self._build_json_card(k, v, child_path)
                card["fields"].append((str(k), f"{{{len(v)}}}", "#666666", child))
                card["children"].append(child)
            elif isinstance(v, list) and v:
                child = self._build_json_card(k, v, child_path)
                card["fields"].append((str(k), f"[{len(v)}]", "#666666", child))
                card["children"].append(child)
            else:
                dv, dc = self._fmt_val(v)
                card["fields"].append((str(k), dv, dc, None))

        card["h"] = self._CARD_MH + max(1, len(card["fields"])) * self._ROW_H + 2
        return card

    def _fmt_val(self, v):
        if isinstance(v, bool):  return ("true" if v else "false"), "#569CD6"
        if v is None:            return "null", "#808080"
        if isinstance(v, str):   return f'"{v}"', "#CE9178"
        return str(v), "#B5CEA8"

    # ── Layout ────────────────────────────────────────────────────────────────

    def _layout_card(self, card: dict, x: int, start_y: int) -> int:
        card["x"] = x
        child_x = x + self._CARD_W + self._COL_GAP
        if not card["children"]:
            card["y"]  = start_y
            card["sh"] = card["h"]
            return card["h"]

        cy = start_y
        for i, child in enumerate(card["children"]):
            cy += self._layout_card(child, child_x, cy)
            if i < len(card["children"]) - 1:
                cy += self._ROW_GAP

        total = cy - start_y
        first_mid = card["children"][0]["y"]  + card["children"][0]["h"]  // 2
        last_mid  = card["children"][-1]["y"] + card["children"][-1]["h"] // 2
        card["y"]  = max(start_y, (first_mid + last_mid) // 2 - card["h"] // 2)
        card["sh"] = max(total, card["h"])
        return card["sh"]

    # ── Desenho ───────────────────────────────────────────────────────────────

    def _draw_json_graph(self, card: dict, ce: set, ca: set):
        self._draw_one_card(card, ce, ca)
        for child in card["children"]:
            self._draw_json_graph(child, ce, ca)

    def _draw_one_card(self, card: dict, ce: set, ca: set):
        z  = self._zoom
        x  = card["x"] * z
        y  = card["y"] * z
        w  = self._CARD_W  * z
        mh = self._CARD_MH * z
        rh = self._ROW_H   * z
        fs = max(6, round(9 * z))

        path  = card["path"]
        has_e = path in ce
        has_a = path in ca
        border = COR_ERRO if has_e else (COR_AVISO if has_a else "#3A3A3A")
        bw = 2 if (has_e or has_a) else 1

        self._canvas.create_rectangle(x, y, x + w, y + card["h"] * z,
                                      fill="#161B22", outline=border, width=bw)
        head_fill = "#3D1010" if has_e else ("#2A2200" if has_a else "#21262D")
        self._canvas.create_rectangle(x + bw - 1, y + bw - 1,
                                      x + w - bw + 1, y + mh,
                                      fill=head_fill, outline="")
        self._canvas.create_line(x + 1, y + mh, x + w - 1, y + mh, fill=border)
        title   = card["title"]
        if len(title) > 24: title = title[:23] + "…"
        title_c = COR_ERRO if has_e else (COR_AVISO if has_a else "#C8C8C8")
        self._canvas.create_text(x + 10 * z, y + mh / 2, text=title,
                                 anchor="w", fill=title_c,
                                 font=("Consolas", fs, "bold"))

        for i, (name, val, color, child_card) in enumerate(card["fields"]):
            fy = y + mh + i * rh
            field_path = f"{path}.{name}" if path else name
            if field_path in ce:
                row_bg, name_c, val_c = "#2D0D0D", COR_ERRO, "#FF8A80"
            elif field_path in ca:
                row_bg, name_c, val_c = "#2A2200", COR_AVISO, "#FFD180"
            else:
                row_bg = "#161B22" if i % 2 == 0 else "#1C2128"
                name_c, val_c = "#9CDCFE", color

            self._canvas.create_rectangle(x + 1, fy, x + w - 1, fy + rh,
                                          fill=row_bg, outline="")
            self._canvas.create_line(x + 1, fy + rh, x + w - 1, fy + rh, fill="#21262D")

            mn = name if len(name) <= 17 else name[:16] + "…"
            self._canvas.create_text(x + 8 * z, fy + rh / 2, text=mn,
                                     anchor="w", fill=name_c, font=("Consolas", fs))
            if child_card is None:
                sv = str(val)
                sv = sv if len(sv) <= 17 else sv[:16] + "…"
                self._canvas.create_text(x + w - 8 * z, fy + rh / 2, text=sv,
                                         anchor="e", fill=val_c, font=("Consolas", fs))
            else:
                self._canvas.create_text(x + w - 10 * z, fy + rh / 2,
                                         text="›", anchor="e", fill="#555555",
                                         font=("Consolas", max(8, round(11 * z))))

    def _draw_connections(self, card: dict):
        z = self._zoom
        for i, (_, __, ___, child_card) in enumerate(card["fields"]):
            if child_card is None:
                continue
            fy = (card["y"] + self._CARD_MH + i * self._ROW_H + self._ROW_H / 2) * z
            fx = (card["x"] + self._CARD_W) * z
            ty = (child_card["y"] + child_card["h"] / 2) * z
            tx =  child_card["x"] * z
            mx = (fx + tx) / 2
            self._canvas.create_line(fx, fy, mx, fy, mx, ty, tx, ty,
                                     fill="#30363D", width=1, smooth=True)
        for child in card["children"]:
            self._draw_connections(child)

    # ── Controles de zoom ─────────────────────────────────────────────────────

    def _zoom_in(self):
        self._zoom = min(3.0, round(self._zoom * 1.25, 2))
        self._redraw_graph()

    def _zoom_out(self):
        self._zoom = max(0.2, round(self._zoom / 1.25, 2))
        self._redraw_graph()

    def _zoom_reset(self):
        self._zoom = 1.0
        self._redraw_graph()

    def _zoom_fit(self):
        if not self._dados_atuais or not hasattr(self, "_canvas"):
            return
        self._canvas.update_idletasks()
        bbox = self._canvas.bbox("all")
        if not bbox:
            return
        content_w = bbox[2] - bbox[0]
        content_h = bbox[3] - bbox[1]
        cw = max(1, self._canvas.winfo_width()  - 20)
        ch = max(1, self._canvas.winfo_height() - 20)
        if content_w > 0 and content_h > 0:
            ajuste = min(cw / content_w, ch / content_h)
            self._zoom = max(0.2, min(3.0, round(self._zoom * ajuste, 2)))
        self._redraw_graph()

    def _redraw_graph(self):
        if not hasattr(self, "_lbl_zoom"):
            return
        self._lbl_zoom.configure(text=f"{round(self._zoom * 100)}%")
        if self._dados_atuais and self._modo_estrutura == "graph":
            ce = getattr(self, "_last_campos_erro",  set())
            ca = getattr(self, "_last_campos_aviso", set())
            self._popular_tree(self._dados_atuais, ce, ca)

    # ── Toggle Graph / Tree ───────────────────────────────────────────────────

    def _trocar_modo_estrutura(self, modo: str):
        self._modo_estrutura = modo
        if modo == "graph":
            self._zoom = 1.0
            if hasattr(self, "_lbl_zoom"):
                self._lbl_zoom.configure(text="100%")
            self._frame_tree.pack_forget()
            self._frame_graph.pack(fill="both", expand=True)
            self._btn_modo_graph.configure(fg_color=COR_BORDA, text_color="white",
                                           border_width=0, font=ctk.CTkFont(size=11, weight="bold"))
            self._btn_modo_tree.configure(fg_color=COR_CARD, text_color=COR_CINZA,
                                          border_width=1, border_color=COR_CINZA,
                                          font=ctk.CTkFont(size=11))
        else:
            self._frame_graph.pack_forget()
            self._frame_tree.pack(fill="both", expand=True)
            self._btn_modo_tree.configure(fg_color=COR_BORDA, text_color="white",
                                          border_width=0, font=ctk.CTkFont(size=11, weight="bold"))
            self._btn_modo_graph.configure(fg_color=COR_CARD, text_color=COR_CINZA,
                                           border_width=1, border_color=COR_CINZA,
                                           font=ctk.CTkFont(size=11))
        if self._dados_atuais:
            ce = getattr(self, "_last_campos_erro",  set())
            ca = getattr(self, "_last_campos_aviso", set())
            self._popular_tree(self._dados_atuais, ce, ca)

    # ── Modo Tree (ttk.Treeview) ──────────────────────────────────────────────

    def _popular_treeview(self, dados: dict, ce: set, ca: set):
        self._treeview.delete(*self._treeview.get_children())
        self._tree_paths = {}
        dados_limpos = {k: v for k, v in dados.items() if not str(k).startswith("_")}
        self._inserir_no_tree("", "raiz", dados_limpos, "")
        for child in self._treeview.get_children():
            self._treeview.item(child, open=True)
        # Destaque de erros
        path_nos: dict[str, list] = {}
        for nid, p in self._tree_paths.items():
            path_nos.setdefault(p, []).append(nid)
        for campo in ca:
            for nid in path_nos.get(campo, []):
                self._treeview.item(nid, tags=("aviso",))
                pai = self._treeview.parent(nid)
                while pai:
                    if "erro" not in self._treeview.item(pai, "tags"):
                        self._treeview.item(pai, tags=("av_pai",))
                    self._treeview.item(pai, open=True)
                    pai = self._treeview.parent(pai)
        for campo in ce:
            for nid in path_nos.get(campo, []):
                self._treeview.item(nid, tags=("erro",))
                pai = self._treeview.parent(nid)
                while pai:
                    self._treeview.item(pai, tags=("erro_pai",))
                    self._treeview.item(pai, open=True)
                    pai = self._treeview.parent(pai)

    def _inserir_no_tree(self, parent: str, chave, valor, path: str):
        cs = str(chave)
        if isinstance(valor, dict):
            no = self._treeview.insert(parent, "end", text=cs,
                                       values=(f"{{{len(valor)}}}",), tags=("obj",))
            self._tree_paths[no] = path
            for k, v in valor.items():
                if str(k).startswith("_"):
                    continue
                self._inserir_no_tree(no, k, v, f"{path}.{k}" if path else str(k))
        elif isinstance(valor, list):
            no = self._treeview.insert(parent, "end", text=cs,
                                       values=(f"[{len(valor)}]",), tags=("arr",))
            self._tree_paths[no] = path
            for i, v in enumerate(valor):
                self._inserir_no_tree(no, i, v, f"{path}[{i}]")
        else:
            if isinstance(valor, bool):   vs, tag = ("true" if valor else "false"), "bool"
            elif valor is None:           vs, tag = "null", "null"
            elif isinstance(valor, str):  vs, tag = f'"{valor}"', "str"
            else:                         vs, tag = str(valor), "num"
            no = self._treeview.insert(parent, "end", text=cs, values=(vs,), tags=(tag,))
            self._tree_paths[no] = path

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

    # ── Importação de Log ─────────────────────────────────────────────────────

    def _importar_log(self):
        caminho = fd.askopenfilename(
            title="Selecionar arquivo de log",
            filetypes=[("Arquivos de log", "*.log"), ("Todos os arquivos", "*.*")],
        )
        if not caminho:
            return
        self._arquivo_log = Path(caminho)
        self._lbl_log.configure(text="⏳ Lendo log...", text_color=COR_AVISO)
        self.update_idletasks()

        try:
            atos = _extrair_atos_do_log(self._arquivo_log)
        except Exception as exc:
            self._lbl_log.configure(
                text=f"⚠ Erro ao ler log: {exc}", text_color=COR_ERRO
            )
            return

        self._atos_log = atos
        self._popular_lista_atos()

    def _popular_lista_atos(self):
        """Popula o frame scrollable com um botão por ato encontrado no log."""
        for widget in self._frame_lista_atos.winfo_children():
            widget.destroy()
        self._btn_atos.clear()

        atos = self._atos_log
        if not atos:
            self._lbl_log.configure(
                text="Nenhum ato encontrado no log.", text_color=COR_AVISO
            )
            self._frame_lista_atos.configure(height=0)
            return

        nome = self._arquivo_log.name if self._arquivo_log else "log"
        self._lbl_log.configure(
            text=f"✔  {nome}  ({len(atos)} ato(s))", text_color=COR_OK
        )

        for i, ato in enumerate(atos):
            label = _label_ato(ato)
            btn = ctk.CTkButton(
                self._frame_lista_atos,
                text=label,
                font=ctk.CTkFont(size=11),
                anchor="w",
                fg_color="transparent",
                hover_color="#3A3A3A",
                text_color=COR_TEXTO,
                height=30,
                corner_radius=6,
                command=lambda idx=i: self._selecionar_ato(idx),
            )
            btn.pack(fill="x", padx=4, pady=2)
            self._btn_atos.append(btn)

        altura = min(len(atos) * 38, 190)
        self._frame_lista_atos.configure(height=altura)

    def _selecionar_ato(self, idx: int):
        """Destaca o ato selecionado e dispara validação."""
        for i, btn in enumerate(self._btn_atos):
            if i == idx:
                btn.configure(fg_color=COR_BORDA, text_color="white")
            else:
                btn.configure(fg_color="transparent", text_color=COR_TEXTO)

        self._dados_log_ato = self._atos_log[idx]
        sistema = self._dados_log_ato.get("_sistema_log", "CEP")
        self._var_sistema.set(sistema)

        if self._validando:
            return
        self._validando = True
        self._btn_validar.configure(text="⏳  Validando...", state="disabled")
        threading.Thread(target=self._validar_em_thread, daemon=True).start()

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
        self._lbl_drop.configure(text="", text_color=COR_OK)

    def _limpar(self):
        self._arquivo_json = None
        self._lbl_arquivo.configure(text="Nenhum arquivo selecionado", text_color=COR_CINZA)
        self._lbl_drop.configure(
            text="",
            text_color=COR_CINZA,
            font=ctk.CTkFont(size=11),
        )
        # Limpa estado do log
        self._atos_log = []
        self._arquivo_log = None
        self._dados_log_ato = None
        self._btn_atos.clear()
        self._lbl_log.configure(text="Nenhum log carregado", text_color=COR_CINZA)
        for widget in self._frame_lista_atos.winfo_children():
            widget.destroy()
        self._frame_lista_atos.configure(height=0)
        self._lbl_resumo_erros.configure(text="")
        self._lbl_resumo_avisos.configure(text="")
        self._lbl_resumo_ok.configure(text="")
        self._lbl_timestamp.configure(text="")
        for txt in (self._txt_resultado, self._txt_tecnico):
            txt.configure(state="normal")
            txt.delete("1.0", "end")
        self._escrever_inicial()
        for txt in (self._txt_resultado, self._txt_tecnico):
            txt.configure(state="disabled")
        self._dados_atuais = None
        if hasattr(self, "_canvas"):
            self._canvas.delete("all")

    def _executar_validacao(self):
        if self._validando:
            return
        if not self._arquivo_json or not self._arquivo_json.exists():
            if self._atos_log:
                self._mostrar_erro_inline("Clique em um ato da lista do log para validar.")
            else:
                self._mostrar_erro_inline("Selecione um arquivo JSON ou importe um arquivo de log.")
            return
        if not self._tabelas_carregadas:
            self._mostrar_erro_inline("Aguarde — os manuais ainda estão sendo carregados...")
            return

        self._dados_log_ato = None
        for btn in self._btn_atos:
            btn.configure(fg_color="transparent", text_color=COR_TEXTO)

        self._validando = True
        self._btn_validar.configure(text="⏳  Validando...", state="disabled")
        threading.Thread(target=self._validar_em_thread, daemon=True).start()

    def _validar_em_thread(self):
        """Roda a validação em thread separada para não travar a UI."""
        if self._dados_log_ato is not None:
            dados = {k: v for k, v in self._dados_log_ato.items() if not k.startswith("_")}
            ato = self._dados_log_ato
            label = _label_ato(ato)
            nome_ref = f"{self._arquivo_log.name if self._arquivo_log else 'log'} — {label}"
            sistema = self._var_sistema.get()
            rel = vs.Relatorio(sistema=sistema, arquivo=nome_ref)
        else:
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

        self._dados_atuais = dados
        self.after(0, self._exibir_relatorio, rel)

    # ── Exibição dos resultados ───────────────────────────────────────────────

    def _escrever_inicial(self):
        for txt in (self._txt_resultado, self._txt_tecnico):
            txt.configure(state="normal")
            self._append("titulo", "  Validador SIGNO\n", txt)
            self._append("cinza",  "  Selecione o sistema (CEP ou CESDI), escolha um arquivo JSON\n", txt)
            self._append("cinza",  "  e clique em VALIDAR para ver o diagnóstico detalhado.\n\n", txt)
            self._append("sep",    "  " + "─" * 58 + "\n\n", txt)
            self._append("cinza",  "  Os resultados aparecerão aqui com destaque por cores:\n\n", txt)
            self._append("erro",   "  [ERRO]   Campo com problema crítico\n", txt)
            self._append("aviso",  "  [AVISO]  Inconsistência ou campo opcional incorreto\n", txt)
            self._append("ok",     "  [OK]     Campo validado com sucesso\n", txt)
            txt.configure(state="disabled")

    def _exibir_relatorio(self, rel: vs.Relatorio):
        for txt in (self._txt_resultado, self._txt_tecnico):
            txt.configure(state="normal")
            txt.delete("1.0", "end")

        ts = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self._lbl_timestamp.configure(text=ts)
        nome_arquivo = Path(rel.arquivo).name

        # ── Aba Técnico ───────────────────────────────────────────────────────
        t = self._txt_tecnico
        self._append("sep",    "  " + "═" * 58 + "\n", t)
        self._append("titulo", f"  Sistema: {rel.sistema}   |   {nome_arquivo}\n", t)
        self._append("sep",    "  " + "═" * 58 + "\n\n", t)

        if not rel.erros and not rel.avisos:
            self._append("ok", "  ✔  JSON VÁLIDO — Nenhum problema encontrado!\n\n", t)
        else:
            if rel.erros:
                self._append("erro", f"  ERROS CRÍTICOS ({len(rel.erros)})\n", t)
                self._append("sep",  "  " + "─" * 56 + "\n", t)
                for campo, msg in rel.erros:
                    self._append("erro",  "  [ERRO]  ", t)
                    self._append("campo", f"{campo}\n", t)
                    for linha in msg.split("\n"):
                        if linha.strip():
                            self._append("seta", "          → ", t)
                            self._append("msg",  linha.strip() + "\n", t)
                    self._append("msg", "\n", t)
            if rel.avisos:
                self._append("aviso", f"  AVISOS / INCONSISTÊNCIAS ({len(rel.avisos)})\n", t)
                self._append("sep",   "  " + "─" * 56 + "\n", t)
                for campo, msg in rel.avisos:
                    self._append("aviso", "  [AVISO] ", t)
                    self._append("campo", f"{campo}\n", t)
                    for linha in msg.split("\n"):
                        if linha.strip():
                            self._append("seta", "          → ", t)
                            self._append("msg",  linha.strip() + "\n", t)
                    self._append("msg", "\n", t)

        self._append("sep",   "  " + "═" * 58 + "\n", t)
        self._append("cinza", "  RESUMO:  ", t)
        self._append("erro",  f"{len(rel.erros)} erro(s)   ", t)
        self._append("aviso", f"{len(rel.avisos)} aviso(s)   ", t)
        self._append("ok",    f"{len(rel.ok)} campo(s) OK\n", t)
        self._append("sep",   "  " + "═" * 58 + "\n", t)

        # ── Aba Simplificado ──────────────────────────────────────────────────
        s = self._txt_resultado
        self._append("sep",    "  " + "═" * 58 + "\n", s)
        self._append("titulo", f"  Sistema: {rel.sistema}   |   {nome_arquivo}\n", s)
        self._append("sep",    "  " + "═" * 58 + "\n\n", s)

        if not rel.erros and not rel.avisos:
            self._append("ok", "  ✔  JSON VÁLIDO — Nenhum problema encontrado!\n\n", s)
        else:
            if rel.erros:
                self._append("erro", f"  ERROS CRÍTICOS ({len(rel.erros)})\n", s)
                self._append("sep",  "  " + "─" * 56 + "\n", s)
                for campo, msg in rel.erros:
                    nome = _traduzir_campo(campo)
                    texto_msg = _traduzir_mensagem(msg)
                    self._append("erro",  "  [ERRO]  ", s)
                    self._append("campo", f"{nome}\n", s)
                    for linha in texto_msg.split("\n"):
                        if linha.strip():
                            self._append("seta", "          → ", s)
                            self._append("msg",  linha.strip() + "\n", s)
                    self._append("msg", "\n", s)
            if rel.avisos:
                self._append("aviso", f"  AVISOS / INCONSISTÊNCIAS ({len(rel.avisos)})\n", s)
                self._append("sep",   "  " + "─" * 56 + "\n", s)
                for campo, msg in rel.avisos:
                    nome = _traduzir_campo(campo)
                    texto_msg = _traduzir_mensagem(msg)
                    self._append("aviso", "  [AVISO] ", s)
                    self._append("campo", f"{nome}\n", s)
                    for linha in texto_msg.split("\n"):
                        if linha.strip():
                            self._append("seta", "          → ", s)
                            self._append("msg",  linha.strip() + "\n", s)
                    self._append("msg", "\n", s)

        self._append("sep",   "  " + "═" * 58 + "\n", s)
        self._append("cinza", "  RESUMO:  ", s)
        self._append("erro",  f"{len(rel.erros)} erro(s)   ", s)
        self._append("aviso", f"{len(rel.avisos)} aviso(s)   ", s)
        self._append("ok",    f"{len(rel.ok)} campo(s) OK\n", s)
        self._append("sep",   "  " + "═" * 58 + "\n", s)

        for txt in (self._txt_resultado, self._txt_tecnico):
            txt.configure(state="disabled")
            txt.see("1.0")

        # Barra de resumo
        icone_e = "✘" if rel.erros else "✔"
        icone_a = "⚠" if rel.avisos else "✔"
        self._lbl_resumo_erros.configure(text=f"  {icone_e}  {len(rel.erros)} erro(s)")
        self._lbl_resumo_avisos.configure(text=f"  {icone_a}  {len(rel.avisos)} aviso(s)")
        self._lbl_resumo_ok.configure(text=f"  ✔  {len(rel.ok)} campo(s) OK")

        campos_erro  = {c for c, _ in rel.erros}
        campos_aviso = {c for c, _ in rel.avisos}
        self._popular_tree(self._dados_atuais, campos_erro, campos_aviso)

        self._btn_validar.configure(text="▶  VALIDAR", state="normal")
        self._validando = False

    def _exibir_erro_json(self, mensagem: str):
        for txt in (self._txt_resultado, self._txt_tecnico):
            txt.configure(state="normal")
            txt.delete("1.0", "end")
            self._append("erro",  "  [ERRO FATAL] JSON com sintaxe inválida\n\n", txt)
            self._append("msg",   f"  {mensagem}\n\n", txt)
            self._append("cinza", "  Verifique se o arquivo é um JSON válido e tente novamente.\n", txt)
            txt.configure(state="disabled")
        self._btn_validar.configure(text="▶  VALIDAR", state="normal")
        self._validando = False

    def _mostrar_erro_inline(self, msg: str):
        for txt in (self._txt_resultado, self._txt_tecnico):
            txt.configure(state="normal")
            txt.delete("1.0", "end")
            self._append("aviso", f"\n  ⚠  {msg}\n", txt)
            txt.configure(state="disabled")

    def _append(self, tag: str, texto: str, widget=None):
        alvo = widget if widget is not None else self._txt_resultado
        alvo.insert("end", texto, tag)

    # ── Carregamento das tabelas ──────────────────────────────────────────────

    def _carregar_tabelas(self):
        # Diretório do executável (fora do _MEIPASS temporário)
        if getattr(sys, "frozen", False):
            _log_dir = Path(sys.executable).parent
        else:
            _log_dir = BASE_DIR
        log_path = _log_dir / "validador_debug.log"

        try:
            with open(log_path, "w", encoding="utf-8") as log:
                log.write(f"BASE_DIR (MEIPASS): {BASE_DIR}\n")
                log.write(f"CEP dir: {BASE_DIR / 'manuais' / 'CEP'} | existe: {(BASE_DIR / 'manuais' / 'CEP').exists()}\n")
                log.write(f"CESDI dir: {BASE_DIR / 'manuais' / 'CESDI'} | existe: {(BASE_DIR / 'manuais' / 'CESDI').exists()}\n")
                manuais_root = BASE_DIR / "manuais"
                if manuais_root.exists():
                    for p in manuais_root.rglob("*"):
                        log.write(f"  arquivo: {p}\n")
                else:
                    log.write("  pasta manuais NAO encontrada!\n")
        except Exception:
            pass

        _stdout_bkp = sys.stdout
        _stderr_bkp = sys.stderr
        buf = io.StringIO()
        sys.stdout = buf
        sys.stderr = buf
        try:
            vs.BASE_DIR = BASE_DIR
            vs.MANUAIS_CEP_DIR   = BASE_DIR / "manuais" / "CEP"
            vs.MANUAIS_CESDI_DIR = BASE_DIR / "manuais" / "CESDI"
            vs.inicializar_tabelas()
            self._tabelas_carregadas = True
            self.after(0, self._on_tabelas_ok)
        except Exception as e:
            import traceback
            msg = traceback.format_exc()
            try:
                with open(log_path, "a", encoding="utf-8") as log:
                    log.write(f"\nEXCEPTION:\n{msg}\n")
            except Exception:
                pass
            self.after(0, self._on_tabelas_erro, str(e))
        finally:
            sys.stdout = _stdout_bkp
            sys.stderr = _stderr_bkp

    def _on_tabelas_ok(self):
        self._lbl_status_tab.configure(
            text="✔ Manuais carregados com sucesso",
            text_color=COR_OK,
        )

    def _on_tabelas_erro(self, msg: str):
        resumo = msg[:60] + "..." if len(msg) > 60 else msg
        self._lbl_status_tab.configure(
            text=f"⚠ Erro: {resumo}",
            text_color=COR_AVISO,
        )
        log_path = BASE_DIR / "validador_debug.log"
        if log_path.exists():
            import os as _os
            try:
                _os.startfile(str(log_path))
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────────────────────
# ENTRADA
# ─────────────────────────────────────────────────────────────────────────────

def main():
    app = ValidadorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
