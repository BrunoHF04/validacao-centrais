# Validador SIGNO — CEP e CESDI

Ferramenta local para validação de arquivos JSON enviados aos sistemas **CEP** (Central de Escrituras e Procurações) e **CESDI** (Central de Separações e Divórcios) da plataforma SIGNO.

---

## Funcionalidades

- Valida **campos obrigatórios**, **tipos de dados** e **formatos de data** (ISO 8601)
- Cruza códigos (`tipoAto`, `naturezaAto`, `qualificacaoParte`, `tipoBemEdireito`, `tipoReferenciaCadastral`) diretamente com as tabelas dos manuais oficiais
- Garante que **CPF, CNPJ, CNS e CEP sejam tratados como strings** (preserva zeros à esquerda)
- Gera relatório detalhado em português com destaque por tipo de problema
- Disponível como **interface gráfica (GUI)** e **linha de comando (CLI)**

---

## Estrutura do Projeto

```
validador-centrais/
├── validador_gui.py          # Interface gráfica (tema escuro moderno)
├── validador_signo.py        # Motor de validação — também funciona via CLI
├── build_exe.bat             # Gera o executável .exe (PyInstaller)
├── requirements.txt          # Dependências Python
├── dist/
│   └── ValidadorSIGNO.exe    # Executável pronto para uso (sem instalar Python)
├── manuais/
│   ├── CEP/
│   │   ├── manualAPICEP v3.csv          # Tabela de tipoAto do CEP
│   │   ├── manualUploadCEP v3.csv       # Tabela de naturezaAto do CEP
│   │   ├── exemploCEP v3.2.csv          # Exemplo de upload CSV
│   │   └── Modelo JSON CEP v3.2.txt     # Modelo de estrutura JSON
│   └── CESDI/
│       ├── manualAPICESDI v2.csv        # Orientações de API CESDI
│       ├── manualUploadCESDI v2.5.xlsx  # Tabelas de códigos (qualidade, bens, etc.)
│       ├── exemploCESDI v2.5.csv        # Exemplo de upload CSV
│       └── Modelo JSON CESDI v2.5.txt   # Modelo de estrutura JSON
└── exemplos/
    ├── cep_valido.json       # JSON CEP sem erros (para teste)
    ├── cep_invalido.json     # JSON CEP com erros intencionais
    ├── cesdi_valido.json     # JSON CESDI sem erros (para teste)
    └── cesdi_invalido.json   # JSON CESDI com erros intencionais
```

---

## Como usar — Interface Gráfica (recomendado)

### Opção A — Executável direto (sem Python)

1. Abra a pasta `dist\`
2. Dê dois cliques em **`ValidadorSIGNO.exe`**
3. Selecione o sistema (**CEP** ou **CESDI**)
4. Arraste o arquivo JSON ou clique em **Procurar arquivo...**
5. Clique em **VALIDAR**

> Os manuais já estão embutidos no `.exe` — nenhuma instalação necessária.

### Opção B — Rodar pelo Python

```bash
python validador_gui.py
```

---

## Como usar — Linha de Comando (CLI)

```bash
# Validar arquivo CEP
python validador_signo.py exemplos/cep_valido.json --sistema CEP

# Validar arquivo CESDI
python validador_signo.py exemplos/cesdi_invalido.json --sistema CESDI

# Ajuda
python validador_signo.py --help
```

O script retorna **exit code 0** se válido e **1** se houver erros — útil para automações e pipelines.

---

## Instalação das dependências

```bash
pip install -r requirements.txt
```

| Pacote | Uso |
|---|---|
| `pandas` | Leitura dos arquivos CSV de manuais |
| `openpyxl` | Leitura do XLSX do manual CESDI |
| `customtkinter` | Interface gráfica moderna (tema escuro) |
| `pyinstaller` | Geração do executável `.exe` |

---

## Regras de validação aplicadas

### Campos raiz

| Campo | CEP | CESDI | Regra |
|---|---|---|---|
| `tipoAto` | obrigatório | obrigatório | Inteiro; cruzado com tabela do manual |
| `naturezaAto` | obrigatório | — | Inteiro; cruzado com tabela do manual |
| `status` / `statusAto` | obrigatório | obrigatório | Inteiro |
| `dataAto` | obrigatório | obrigatório | String ISO 8601 (`YYYY-MM-DD`) |
| `livroInicial` | obrigatório | obrigatório | Inteiro |
| `folhaInicial` | obrigatório | obrigatório | Inteiro |
| `folhaFinal` | obrigatório | obrigatório | Inteiro |

### Partes

| Campo | Regra |
|---|---|
| `nomeParte` | String obrigatória |
| `qualificacaoParte` | Inteiro; cruzado com tabela `QualidadeDaParte` do XLSX |
| `cpf` | **String** (preserva zeros à esquerda) |
| `cpfConjuge` | **String** com 11 dígitos |
| `cep` / `cepResidencia` | **String** com 8 dígitos |
| `dataNascimento`, `dataCasamento`, etc. | ISO 8601 |
| `filiacoes` | Lista de strings |
| `semFiliacoes` / `naoPossuiFiliacao` | Booleano |

### Bens e Direitos

| Campo | Regra |
|---|---|
| `tipoBemEdireito` | Cruzado com aba `TipoBensEDireito` do XLSX CESDI |
| `referenciaCadastralImovel` | Cruzado com aba `TipoReferenciaCadastral` do XLSX |
| `cep` do imóvel | **String** com 8 dígitos |
| `cin` | String |
| CPF dos titulares | **String** |

---

## Recompilar o `.exe`

Ao atualizar os manuais ou o código, regenere o executável dando dois cliques em:

```
build_exe.bat
```

O script verifica dependências, compila e abre a pasta `dist\` automaticamente.

---

## Manuais utilizados

- **CEP v3.2** — `manualAPICEP v3.csv`, `manualUploadCEP v3.csv`, `Modelo JSON CEP v3.2.txt`
- **CESDI v2.5** — `manualAPICESDI v2.csv`, `manualUploadCESDI v2.5.xlsx`, `Modelo JSON CESDI v2.5.txt`
