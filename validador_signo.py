#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validador local de JSON para os sistemas CEP e CESDI da SIGNO.
Analisa campos obrigatórios, tipos de dados, formatos e cruza códigos
com as tabelas dos manuais oficiais.

Uso:
    python validador_signo.py <arquivo.json> --sistema [CEP|CESDI]
    python validador_signo.py exemplos/cep_valido.json --sistema CEP
    python validador_signo.py exemplos/cesdi_invalido.json --sistema CESDI
"""

import argparse
import io
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# Garante UTF-8 na saída do console (no-op quando rodando como .exe sem console)
try:
    if sys.stdout is not None and hasattr(sys.stdout, "encoding") \
            and sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if sys.stderr is not None and hasattr(sys.stderr, "encoding") \
            and sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

import pandas as pd

# ─────────────────────────────────────────────
# CONSTANTES DE LOCALIZAÇÃO DOS MANUAIS
# Compatível com PyInstaller (sys._MEIPASS) e execução normal
# ─────────────────────────────────────────────
def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent

BASE_DIR = _get_base_dir()
MANUAIS_CEP_DIR = BASE_DIR / "manuais" / "CEP"
MANUAIS_CESDI_DIR = BASE_DIR / "manuais" / "CESDI"

# ─────────────────────────────────────────────
# CARREGAMENTO DAS TABELAS DOS MANUAIS
# ─────────────────────────────────────────────

def carregar_tabela_csv(caminho: Path) -> dict:
    """Lê CSV com separador ';' e retorna dicionário {código: descrição}."""
    try:
        df = pd.read_csv(caminho, sep=";", encoding="utf-8-sig", dtype=str)
        df.columns = [c.strip() for c in df.columns]
        # Primeira coluna = código, segunda = descrição
        col_codigo = df.columns[0]
        col_desc = df.columns[1]
        df[col_codigo] = df[col_codigo].str.strip()
        df[col_desc] = df[col_desc].str.strip()
        return {row[col_codigo]: row[col_desc] for _, row in df.iterrows()
                if pd.notna(row[col_codigo]) and row[col_codigo].isdigit()}
    except Exception as e:
        print(f"  [AVISO] Não foi possível carregar {caminho}: {e}")
        return {}


def carregar_tabela_xlsx(caminho: Path, aba: str, col_codigo: int = 0, col_desc: int = 1,
                          skiprows: int = 1) -> dict:
    """Lê aba de XLSX e retorna dicionário {código: descrição}."""
    try:
        df = pd.read_excel(caminho, sheet_name=aba, dtype=str, header=skiprows)
        resultado = {}
        for _, row in df.iterrows():
            vals = list(row)
            cod = str(vals[col_codigo]).strip() if col_codigo < len(vals) else ""
            desc = str(vals[col_desc]).strip() if col_desc < len(vals) else ""
            if cod and cod not in ("nan", "None") and re.match(r"^\d+$", cod):
                resultado[cod] = desc
        return resultado
    except Exception as e:
        print(f"  [AVISO] Não foi possível carregar aba '{aba}' de {caminho}: {e}")
        return {}


def carregar_tabelas_cesdi_xlsx(caminho: Path) -> dict:
    """Carrega todas as abas relevantes do XLSX do CESDI."""
    tabelas = {}
    mapa_abas = {
        "qualidadeParte":         ("QualidadeDaParte",       1, 2, 1),
        "tipoBemEdireito":        ("TipoBensEDireito",        0, 1, 0),
        "tipoReferenciaCadastral":("TipoReferenciaCadastral", 0, 1, 0),
    }
    try:
        import openpyxl
        wb = openpyxl.load_workbook(caminho, data_only=True)
    except Exception as e:
        print(f"  [AVISO] Não foi possível abrir {caminho}: {e}")
        return tabelas

    for chave, (nome_aba, col_c, col_d, skip) in mapa_abas.items():
        try:
            ws = wb[nome_aba]
            resultado = {}
            rows = list(ws.iter_rows(values_only=True))
            data_rows = rows[skip + 1:]  # pula cabeçalho
            for row in data_rows:
                if not row or len(row) <= max(col_c, col_d):
                    continue
                cod = str(row[col_c]).strip() if row[col_c] is not None else ""
                desc = str(row[col_d]).strip() if row[col_d] is not None else ""
                if re.match(r"^\d+$", cod):
                    resultado[cod] = desc
            tabelas[chave] = resultado
        except Exception as e:
            print(f"  [AVISO] Aba '{nome_aba}': {e}")
            tabelas[chave] = {}

    # Extrai tipoAto dos cabeçalhos da aba QualidadeDaParte (ex: "Separação (1)")
    try:
        ws_qp = wb["QualidadeDaParte"]
        tipos_ato = {}
        for row in ws_qp.iter_rows(values_only=True):
            if not row or row[0] is None:
                continue
            celula = str(row[0]).strip()
            # Padrão: "Descrição (N)" ou "Descrição (N)" com número ao final
            m = re.match(r"^(.+?)\s*\((\d+)\)\s*$", celula)
            if m:
                desc_ato = m.group(1).strip()
                cod_ato = m.group(2)
                tipos_ato[cod_ato] = desc_ato
        if tipos_ato:
            tabelas["tipoAto"] = tipos_ato
    except Exception as e:
        print(f"  [AVISO] Não foi possível extrair tipoAto do XLSX: {e}")

    return tabelas


# ─────────────────────────────────────────────
# CARREGAMENTO GLOBAL DAS TABELAS
# ─────────────────────────────────────────────

TABELAS_CEP = {}
TABELAS_CESDI = {}

def inicializar_tabelas():
    global TABELAS_CEP, TABELAS_CESDI

    # CEP: tipoAto / naturezaAto vêm do mesmo arquivo de manual
    TABELAS_CEP["tipoAto"] = carregar_tabela_csv(MANUAIS_CEP_DIR / "manualAPICEP v3.csv")
    TABELAS_CEP["naturezaAto"] = carregar_tabela_csv(MANUAIS_CEP_DIR / "manualUploadCEP v3.csv")

    # CESDI: tabelas adicionais do XLSX (inclui tipoAto extraído da aba QualidadeDaParte)
    xlsx = MANUAIS_CESDI_DIR / "manualUploadCESDI v2.5.xlsx"
    extras = carregar_tabelas_cesdi_xlsx(xlsx)
    TABELAS_CESDI.update(extras)

    # Fallback: se tipoAto não foi extraído do XLSX, usa tabela fixa do manual
    if not TABELAS_CESDI.get("tipoAto"):
        TABELAS_CESDI["tipoAto"] = {
            "1": "Separação",
            "2": "Reconciliação",
            "3": "Conversão de Separação em Divórcio",
            "4": "Divórcio Direto",
            "5": "Inventário",
            "6": "Sobrepartilha",
            "7": "Rerratificação",
            "8": "Nomeação de Inventariante",
            "9": "Partilha",
        }

    # Códigos de qualificacaoParte comuns ao CEP (baseados no modelo)
    # O manual CEP não tem aba separada, usamos os mesmos do CESDI como referência
    TABELAS_CEP["qualificacaoParte"] = TABELAS_CESDI.get("qualidadeParte", {})


# ─────────────────────────────────────────────
# UTILITÁRIOS DE VALIDAÇÃO
# ─────────────────────────────────────────────

class Relatorio:
    def __init__(self, sistema: str, arquivo: str):
        self.sistema = sistema
        self.arquivo = arquivo
        self.erros = []
        self.avisos = []
        self.ok = []

    def erro(self, campo: str, mensagem: str):
        self.erros.append((campo, mensagem))

    def aviso(self, campo: str, mensagem: str):
        self.avisos.append((campo, mensagem))

    def sucesso(self, campo: str, mensagem: str = ""):
        self.ok.append((campo, mensagem))

    def imprimir(self):
        sep = "=" * 70
        print(f"\n{sep}")
        print(f"  RELATÓRIO DE VALIDAÇÃO SIGNO — {self.sistema}")
        print(f"  Arquivo: {self.arquivo}")
        print(f"  Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print(sep)

        if not self.erros and not self.avisos:
            print("\n  [OK] JSON VALIDO -- Nenhum problema encontrado.\n")
        else:
            if self.erros:
                print(f"\n  [ERRO] ERROS CRITICOS ({len(self.erros)}):\n")
                for campo, msg in self.erros:
                    print(f"    [ERRO]  {campo}")
                    print(f"            -> {msg}\n")

            if self.avisos:
                print(f"\n  [AVISO] INCONSISTENCIAS ({len(self.avisos)}):\n")
                for campo, msg in self.avisos:
                    print(f"    [AVISO] {campo}")
                    print(f"            -> {msg}\n")

        print(f"  Resumo: {len(self.erros)} erro(s), {len(self.avisos)} aviso(s), "
              f"{len(self.ok)} campo(s) OK.")
        print(sep + "\n")

    @property
    def valido(self) -> bool:
        return len(self.erros) == 0


# ─────────────────────────────────────────────
# FUNÇÕES DE VALIDAÇÃO AUXILIARES
# ─────────────────────────────────────────────

def validar_data_iso(valor, campo: str, rel: Relatorio, obrigatorio: bool = False):
    """Verifica formato ISO 8601 (YYYY-MM-DD ou YYYY-MM-DDTHH:MM:SS.sssZ)."""
    if valor is None or valor == "":
        if obrigatorio:
            rel.erro(campo, "Campo obrigatório não informado.")
        return
    if not isinstance(valor, str):
        rel.erro(campo, f"Esperado string com data ISO 8601, recebido {type(valor).__name__}: {valor!r}")
        return
    # Aceita YYYY-MM-DD ou YYYY-MM-DDTHH:MM:SS... 
    padrao = r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?)?$"
    if not re.match(padrao, valor):
        rel.erro(campo, f"Formato de data inválido: {valor!r}. Use ISO 8601 (ex: 2024-06-01 ou 2024-06-01T00:00:00.000Z).")
    else:
        rel.sucesso(campo, f"Data OK: {valor}")


def validar_string_campo_obrigatorio(valor, campo: str, rel: Relatorio):
    if valor is None or (isinstance(valor, str) and valor.strip() == ""):
        rel.erro(campo, "Campo string obrigatório está ausente ou vazio.")
    elif not isinstance(valor, str):
        rel.erro(campo, f"Deve ser uma string, mas recebeu {type(valor).__name__}: {valor!r}")
    else:
        rel.sucesso(campo)


def validar_inteiro(valor, campo: str, rel: Relatorio, obrigatorio: bool = True,
                     valores_validos: dict = None, nome_tabela: str = ""):
    """Valida que o campo é inteiro e, opcionalmente, cruza com tabela de códigos."""
    if valor is None:
        if obrigatorio:
            rel.erro(campo, "Campo inteiro obrigatório não informado.")
        return
    if not isinstance(valor, int) or isinstance(valor, bool):
        rel.erro(campo, f"Tipo inválido: esperado inteiro, recebido {type(valor).__name__}: {valor!r}")
        return
    if valores_validos is not None:
        chave = str(valor)
        if chave not in valores_validos:
            codigos_disponiveis = ", ".join(
                f"{k}={v}" for k, v in sorted(valores_validos.items(), key=lambda x: int(x[0]))
            )
            rel.erro(campo,
                     f"Código {valor} não reconhecido na tabela '{nome_tabela}'.\n"
                     f"            Códigos válidos: {codigos_disponiveis}")
        else:
            rel.sucesso(campo, f"Código {valor} → {valores_validos[chave]}")


def validar_string_numerica(valor, campo: str, rel: Relatorio,
                             comprimento: int = None, nome: str = ""):
    """
    Valida CPF, CNPJ, CNS, CEP — devem ser strings preservando zeros à esquerda.
    """
    if valor is None or valor == "":
        return  # campo opcional; obrigatoriedade checada separadamente
    if not isinstance(valor, str):
        rel.erro(campo,
                 f"{nome or campo} deve ser string (para preservar zeros à esquerda), "
                 f"mas recebeu {type(valor).__name__}: {valor!r}")
        return
    # Remove formatação para contar dígitos
    apenas_digitos = re.sub(r"[.\-/]", "", valor).strip()
    if comprimento and len(apenas_digitos) != comprimento:
        rel.aviso(campo,
                  f"{nome or campo} tem {len(apenas_digitos)} dígito(s); "
                  f"esperado {comprimento}. Valor: {valor!r}")
    else:
        rel.sucesso(campo, f"{nome or campo} OK: {valor}")


def campo_presente(dados: dict, campo: str) -> bool:
    return campo in dados and dados[campo] is not None


# ─────────────────────────────────────────────
# VALIDAÇÃO CEP
# ─────────────────────────────────────────────

def validar_cep_json(dados: dict, rel: Relatorio):
    tabelas = TABELAS_CEP

    # ── Campos raiz obrigatórios ──────────────────────────────────
    campos_int_obrig = {
        "tipoAto":       ("tipoAto",     tabelas.get("tipoAto", {})),
        "naturezaAto":   ("naturezaAto", tabelas.get("naturezaAto", {})),
        "status":        ("status",      {}),
        "livroInicial":  ("livroInicial",{}),
        "folhaInicial":  ("folhaInicial",{}),
        "folhaFinal":    ("folhaFinal",  {}),
    }
    for campo, (nome_tab, tab) in campos_int_obrig.items():
        validar_inteiro(dados.get(campo), campo, rel, obrigatorio=True,
                        valores_validos=tab if tab else None,
                        nome_tabela=nome_tab if tab else "")

    # ── Campos inteiros opcionais ─────────────────────────────────
    # Nota: complemento* são strings alfanuméricas, não inteiros
    campos_int_opcionais = [
        "tipoInvalidacaoAto", "livroFinal",
        "valorOperacao", "prazoPagamento", "formaPagamento",
        "existeBemEdireito", "naturezaLitigio", "acordo",
    ]
    for campo in campos_int_opcionais:
        v = dados.get(campo)
        if v is not None and not isinstance(v, (int, float)) or isinstance(v, bool):
            if campo in dados and isinstance(dados[campo], str) and not dados[campo].isdigit():
                rel.aviso(campo, f"Esperado número, recebeu string: {dados[campo]!r}")

    # ── Campos de data ────────────────────────────────────────────
    validar_data_iso(dados.get("dataAto"),      "dataAto",      rel, obrigatorio=True)
    validar_data_iso(dados.get("dataContrato"), "dataContrato", rel)
    validar_data_iso(dados.get("dataInclusao"), "dataInclusao", rel)

    # ── Campo reservaDePoderes (booleano) ─────────────────────────
    if "reservaDePoderes" in dados:
        if not isinstance(dados["reservaDePoderes"], bool):
            rel.aviso("reservaDePoderes", f"Esperado booleano, recebeu: {dados['reservaDePoderes']!r}")

    # ── Partes ────────────────────────────────────────────────────
    partes = dados.get("partes", [])
    if not isinstance(partes, list):
        rel.erro("partes", "Campo 'partes' deve ser uma lista.")
    elif len(partes) == 0:
        rel.aviso("partes", "Nenhuma parte informada no ato.")
    else:
        for i, parte in enumerate(partes):
            prefixo = f"partes[{i}]"
            _validar_parte_cep(parte, i, prefixo, rel)

    # ── Bens e Direitos ───────────────────────────────────────────
    bens = dados.get("bensEdireitos", [])
    if isinstance(bens, list):
        for i, bem in enumerate(bens):
            _validar_bem_cep(bem, i, f"bensEdireitos[{i}]", rel)

    # ── Atos de Origem ───────────────────────────────────────────
    atos_origem = dados.get("atosOrigem", [])
    if isinstance(atos_origem, list):
        for i, ao in enumerate(atos_origem):
            _validar_ato_origem_cep(ao, i, f"atosOrigem[{i}]", rel)

    # ── Attachments ───────────────────────────────────────────────
    attachments = dados.get("attachments", [])
    if isinstance(attachments, list):
        for i, att in enumerate(attachments):
            prefixo = f"attachments[{i}]"
            for campo in ["base64Content", "extensaoArquivo", "nome"]:
                if not att.get(campo):
                    rel.aviso(f"{prefixo}.{campo}", f"Campo de anexo vazio ou ausente.")


def _validar_parte_cep(parte: dict, idx: int, prefixo: str, rel: Relatorio):
    tabelas = TABELAS_CEP

    # qualificacaoParte obrigatório
    validar_inteiro(parte.get("qualificacaoParte"), f"{prefixo}.qualificacaoParte", rel,
                    obrigatorio=True,
                    valores_validos=tabelas.get("qualificacaoParte"),
                    nome_tabela="qualificacaoParte")

    # nomeParte obrigatório
    validar_string_campo_obrigatorio(parte.get("nomeParte"), f"{prefixo}.nomeParte", rel)

    # CPF / CNPJ: deve ser string
    validar_string_numerica(parte.get("cpf"), f"{prefixo}.cpf", rel, nome="CPF/CNPJ")

    # cpfConjuge: deve ser string
    if parte.get("cpfConjuge"):
        validar_string_numerica(parte["cpfConjuge"], f"{prefixo}.cpfConjuge", rel,
                                comprimento=11, nome="CPF do Cônjuge")

    # CEP: deve ser string
    if parte.get("cep"):
        validar_string_numerica(parte["cep"], f"{prefixo}.cep", rel,
                                comprimento=8, nome="CEP")

    # datas
    for campo_data in ["dataCasamento", "dataEmissao", "dataNascimento", "dataObito"]:
        if parte.get(campo_data):
            validar_data_iso(parte[campo_data], f"{prefixo}.{campo_data}", rel)

    # inteiros opcionais com domínio
    for campo in ["estadoCivil", "genero", "tipoDocumento", "tipoContato",
                  "capacidadeCivil", "areaAtuacao", "profissao", "regimeBens",
                  "municipio", "nacionalidade", "paisOrigem"]:
        v = parte.get(campo)
        if v is not None and not isinstance(v, int):
            rel.aviso(f"{prefixo}.{campo}", f"Esperado inteiro, recebido: {type(v).__name__} = {v!r}")

    # semFiliacoes: booleano
    if "semFiliacoes" in parte:
        if not isinstance(parte["semFiliacoes"], bool):
            rel.aviso(f"{prefixo}.semFiliacoes", f"Esperado booleano, recebido: {parte['semFiliacoes']!r}")

    # filiacoes: lista de strings
    filiacoes = parte.get("filiacoes", [])
    if filiacoes and not isinstance(filiacoes, list):
        rel.erro(f"{prefixo}.filiacoes", "Campo 'filiacoes' deve ser uma lista de strings.")


def _validar_bem_cep(bem: dict, idx: int, prefixo: str, rel: Relatorio):
    # cep do imóvel: string
    if bem.get("cep"):
        validar_string_numerica(bem["cep"], f"{prefixo}.cep", rel, comprimento=8, nome="CEP do imóvel")

    # cin: string (Código Imobiliário Nacional)
    if bem.get("cin") and not isinstance(bem["cin"], str):
        rel.erro(f"{prefixo}.cin", f"CIN deve ser string, recebido: {type(bem['cin']).__name__}")

    # valor: numérico
    for campo_num in ["valor", "valorFiscal", "valorImovel",
                       "quantidadeAreaConstruida", "quantidadeAreaTotal"]:
        v = bem.get(campo_num)
        if v is not None and not isinstance(v, (int, float)):
            rel.aviso(f"{prefixo}.{campo_num}",
                      f"Esperado número, recebido {type(v).__name__}: {v!r}")

    # titulares
    titulares = bem.get("titulares", [])
    if isinstance(titulares, list):
        for j, tit in enumerate(titulares):
            if tit.get("cpf") and not isinstance(tit["cpf"], str):
                rel.erro(f"{prefixo}.titulares[{j}].cpf",
                         f"CPF do titular deve ser string (preserva zeros à esquerda).")


def _validar_ato_origem_cep(ao: dict, idx: int, prefixo: str, rel: Relatorio):
    # CNS: string
    if ao.get("numeroCns") and not isinstance(ao["numeroCns"], str):
        rel.erro(f"{prefixo}.numeroCns", "CNS deve ser string (preserva zeros à esquerda).")

    # booleans
    for campo_bool in ["atosAnteriores", "cartorioAtual", "outroCartorio"]:
        v = ao.get(campo_bool)
        if v is not None and not isinstance(v, bool):
            rel.aviso(f"{prefixo}.{campo_bool}", f"Esperado booleano, recebido: {v!r}")


# ─────────────────────────────────────────────
# VALIDAÇÃO CESDI
# ─────────────────────────────────────────────

def validar_cesdi_json(dados: dict, rel: Relatorio):
    tabelas = TABELAS_CESDI

    # ── Campos raiz obrigatórios ──────────────────────────────────
    validar_inteiro(dados.get("tipoAto"), "tipoAto", rel, obrigatorio=True,
                    valores_validos=tabelas.get("tipoAto", {}),
                    nome_tabela="tipoAto CESDI")

    validar_inteiro(dados.get("statusAto"), "statusAto", rel, obrigatorio=True)

    validar_data_iso(dados.get("dataAto"), "dataAto", rel, obrigatorio=True)

    for campo in ["livroInicial", "folhaInicial", "folhaFinal"]:
        validar_inteiro(dados.get(campo), campo, rel, obrigatorio=True)

    # ── Campos de data opcionais ──────────────────────────────────
    for campo_data in ["dataContrato", "dataCasamento"]:
        if dados.get(campo_data):
            validar_data_iso(dados[campo_data], campo_data, rel)

    # ── Campos inteiros opcionais ─────────────────────────────────
    for campo in ["livroFinal", "prazoPagamento", "formaPagamento",
                  "regimeDeBensDireitosDoCasamento", "quantidadefilhosMaiores",
                  "quantidadefilhosMenores", "municipioCartorioAtoOrigem", "tipoAtoOrigem"]:
        v = dados.get(campo)
        if v is not None and not isinstance(v, int):
            rel.aviso(campo, f"Esperado inteiro, recebido {type(v).__name__}: {v!r}")

    # ── existeBemEdireitoVinculadoAoAto: string (0 ou 1 como texto?) ─
    v_bem = dados.get("existeBemEdireitoVinculadoAoAto")
    if v_bem is not None and not isinstance(v_bem, str):
        rel.aviso("existeBemEdireitoVinculadoAoAto",
                  f"Esperado string, recebido {type(v_bem).__name__}: {v_bem!r}")

    # ── Booleans ──────────────────────────────────────────────────
    for campo_bool in ["cartorioAtual", "cartorioNaoCadastrado"]:
        v = dados.get(campo_bool)
        if v is not None and not isinstance(v, bool):
            rel.aviso(campo_bool, f"Esperado booleano, recebido: {v!r}")

    # ── Partes ────────────────────────────────────────────────────
    partes = dados.get("partes", [])
    if not isinstance(partes, list):
        rel.erro("partes", "Campo 'partes' deve ser uma lista.")
    elif len(partes) == 0:
        rel.aviso("partes", "Nenhuma parte informada no ato.")
    else:
        for i, parte in enumerate(partes):
            _validar_parte_cesdi(parte, i, f"partes[{i}]", rel)

    # ── Bens e Direitos ───────────────────────────────────────────
    bens = dados.get("bensEdireitos", [])
    if isinstance(bens, list):
        for i, bem in enumerate(bens):
            _validar_bem_cesdi(bem, i, f"bensEdireitos[{i}]", rel)

    # ── Anexos ───────────────────────────────────────────────────
    for lista_anexos in ["anexos", "anexosEspecificos"]:
        for i, att in enumerate(dados.get(lista_anexos, [])):
            prefixo = f"{lista_anexos}[{i}]"
            for campo in ["base64Content", "extensaoArquivo", "nome"]:
                if not att.get(campo):
                    rel.aviso(f"{prefixo}.{campo}", "Campo de anexo vazio ou ausente.")


def _validar_parte_cesdi(parte: dict, idx: int, prefixo: str, rel: Relatorio):
    tabelas = TABELAS_CESDI

    # qualificacaoParte
    validar_inteiro(parte.get("qualificacaoParte"), f"{prefixo}.qualificacaoParte", rel,
                    obrigatorio=True,
                    valores_validos=tabelas.get("qualidadeParte"),
                    nome_tabela="QualidadeDaParte (XLSX)")

    # nomeParte obrigatório
    validar_string_campo_obrigatorio(parte.get("nomeParte"), f"{prefixo}.nomeParte", rel)

    # CPF: deve ser string
    validar_string_numerica(parte.get("cpf"), f"{prefixo}.cpf", rel, nome="CPF/CNPJ")

    # CEP: deve ser string
    if parte.get("cepResidencia"):
        validar_string_numerica(parte["cepResidencia"], f"{prefixo}.cepResidencia", rel,
                                comprimento=8, nome="CEP de residência")

    # cpfConjuge: string
    if parte.get("cpfConjuge"):
        validar_string_numerica(parte["cpfConjuge"], f"{prefixo}.cpfConjuge", rel,
                                comprimento=11, nome="CPF do Cônjuge")

    # datas
    for campo_data in ["dataEmissaoDocumento", "dataNascimentoParte",
                       "dataCasamento", "dataObito"]:
        if parte.get(campo_data):
            validar_data_iso(parte[campo_data], f"{prefixo}.{campo_data}", rel)

    # inteiros
    for campo in ["tipoDocumento", "genero", "capacidadeCivil", "estadoCivilParte",
                  "tipoContatoParte", "cidadeResidencia", "codigoPaisParte",
                  "codigoPaisResidencia", "nacionalidadeParte", "regimeDeBensDireitosDoCasamento"]:
        v = parte.get(campo)
        if v is not None and not isinstance(v, int):
            rel.aviso(f"{prefixo}.{campo}", f"Esperado inteiro, recebido {type(v).__name__}: {v!r}")

    # booleans
    for campo_bool in ["responsavelFilhosMenores", "naoPossuiFiliacao"]:
        v = parte.get(campo_bool)
        if v is not None and not isinstance(v, bool):
            rel.aviso(f"{prefixo}.{campo_bool}", f"Esperado booleano, recebido: {v!r}")

    # filiacoes: lista
    filiacoes = parte.get("filiacoes", [])
    if filiacoes and not isinstance(filiacoes, list):
        rel.erro(f"{prefixo}.filiacoes", "Campo 'filiacoes' deve ser lista de strings.")


def _validar_bem_cesdi(bem: dict, idx: int, prefixo: str, rel: Relatorio):
    tabelas = TABELAS_CESDI

    # tipoBemEdireito
    validar_inteiro(bem.get("tipoBemEdireito"), f"{prefixo}.tipoBemEdireito", rel,
                    obrigatorio=False,
                    valores_validos=tabelas.get("tipoBemEdireito"),
                    nome_tabela="TipoBensEDireito (XLSX)")

    # tipoReferenciaCadastral
    if "referenciaCadastralImovel" in bem:
        validar_inteiro(bem.get("referenciaCadastralImovel"),
                        f"{prefixo}.referenciaCadastralImovel", rel,
                        obrigatorio=False,
                        valores_validos=tabelas.get("tipoReferenciaCadastral"),
                        nome_tabela="TipoReferenciaCadastral (XLSX)")

    # CEP do imóvel: string
    if bem.get("cep"):
        validar_string_numerica(bem["cep"], f"{prefixo}.cep", rel,
                                comprimento=8, nome="CEP do imóvel")

    # CIN: string
    if bem.get("cin") and not isinstance(bem["cin"], str):
        rel.erro(f"{prefixo}.cin", "CIN deve ser string.")

    # numéricos
    for campo_num in ["valorDoBem", "valorImovel", "valorFiscal",
                       "quantidadeAreaTotal", "quantidadeUnidadeAreaConstruida"]:
        v = bem.get(campo_num)
        if v is not None and not isinstance(v, (int, float)):
            rel.aviso(f"{prefixo}.{campo_num}",
                      f"Esperado número, recebido {type(v).__name__}: {v!r}")

    # titulares
    titulares = bem.get("titulares", [])
    if isinstance(titulares, list):
        for j, tit in enumerate(titulares):
            if tit.get("cpf") and not isinstance(tit["cpf"], str):
                rel.erro(f"{prefixo}.titulares[{j}].cpf",
                         "CPF do titular deve ser string (preserva zeros à esquerda).")


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Validador local de JSON para sistemas CEP e CESDI da SIGNO."
    )
    parser.add_argument("arquivo", help="Caminho para o arquivo JSON a ser validado.")
    parser.add_argument(
        "--sistema", "-s",
        choices=["CEP", "CESDI"],
        required=True,
        help="Sistema alvo: CEP ou CESDI."
    )
    args = parser.parse_args()

    # Verifica existência do arquivo
    caminho_json = Path(args.arquivo)
    if not caminho_json.exists():
        print(f"\n[ERRO] Arquivo não encontrado: {caminho_json}")
        sys.exit(1)

    # Lê JSON
    try:
        with open(caminho_json, encoding="utf-8") as f:
            dados = json.load(f)
    except json.JSONDecodeError as e:
        print(f"\n[ERRO FATAL] JSON inválido (erro de sintaxe): {e}")
        sys.exit(1)

    # Carrega tabelas dos manuais
    print(f"\nCarregando tabelas dos manuais...")
    inicializar_tabelas()
    print("  OK — Tabelas carregadas.")

    # Valida
    rel = Relatorio(sistema=args.sistema, arquivo=str(caminho_json))

    if args.sistema == "CEP":
        validar_cep_json(dados, rel)
    else:
        validar_cesdi_json(dados, rel)

    rel.imprimir()
    sys.exit(0 if rel.valido else 1)


if __name__ == "__main__":
    main()
