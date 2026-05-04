# Validador SIGNO — CEP e CESDI

Ferramenta local para validação de arquivos JSON enviados aos sistemas **CEP** (Central de Escrituras e Procurações) e **CESDI** (Central de Separações e Divórcios) da plataforma SIGNO.

---

## Funcionalidades

- Valida **campos obrigatórios**, **tipos de dados** e **formatos de data** (ISO 8601)
- Cruza códigos (`tipoAto`, `naturezaAto`, `qualificacaoParte`, `tipoBemEdireito`, `tipoReferenciaCadastral`) diretamente com as tabelas dos manuais oficiais
- Garante que **CPF, CNPJ, CNS e CEP sejam tratados como strings** (preserva zeros à esquerda)
- Gera relatório detalhado em português com destaque por tipo de problema
- Disponível como **interface gráfica (GUI)** e **linha de comando (CLI)**
- **Importação de arquivo de log** do Orion/SIGNO com extração automática dos atos JSON
- **Visualizador de estrutura JSON** com dois modos: Graph (canvas interativo) e Tree (árvore hierárquica)
- **Tema claro e escuro** com alternância em tempo real

---

## Estrutura do Projeto

```
validador-centrais/
├── validador_gui.py          # Interface gráfica (tema escuro/claro moderno)
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

## Importação de Arquivo de Log

O sistema pode ler diretamente o arquivo de log gerado pelo Orion/SIGNO (`wsOrionSigno.log`), sem precisar copiar e colar JSON manualmente.

1. Clique em **Importar Log...** no painel esquerdo
2. Selecione o arquivo `.log`
3. O sistema extrai automaticamente todos os atos (JSON `jsonEntrada`) presentes no log
4. Os atos são listados por **Livro e Folha** e deduplicados automaticamente
5. Clique em qualquer ato da lista para validá-lo instantaneamente

---

## Visualizador de Estrutura JSON

A aba **Estrutura** exibe visualmente o JSON validado. Há dois modos de visualização:

### Modo Graph (padrão)
- Cards conectados por linhas, estilo JSON Crack
- **Erros em vermelho** — card com borda vermelha, cabeçalho tingido e campo destacado
- **Avisos em laranja** — mesma lógica com cor laranja
- **Propagação visual** — cards ancestrais de um erro ficam com borda vermelha fraca, indicando que há um problema dentro deles
- **Zoom**: botões `−` / `+` / `⊡ Fit` / `1:1` ou `Ctrl + Scroll`
- **Pan**: clique e arraste para navegar pelo canvas
- **Tela cheia**: botão `⛶` abre visualização maximizada com controles independentes

### Modo Tree
- Árvore hierárquica com campos e valores
- Campos com erro destacados em **vermelho negrito**
- Campos com aviso destacados em **laranja negrito**
- Nós ancestrais marcados para facilitar a localização do problema

---

## Interface e Temas

| Elemento | Descrição |
|---|---|
| Botão `🌙 / ☀` | Alterna entre tema escuro e claro (ao lado do botão `?`) |
| Scrollbars | Estilo compacto e escuro (8 px), adaptadas ao tema ativo |
| Painel esquerdo | Sistema, arquivo JSON e lista de atos do log |
| Painel direito | Abas Simplificado, Técnico e Estrutura |
| Barra de status | Contagem de erros, avisos e campos OK |

---

## Instalação das dependências

```bash
pip install -r requirements.txt
```

| Pacote | Uso |
|---|---|
| `pandas` | Leitura dos arquivos CSV de manuais |
| `openpyxl` | Leitura do XLSX do manual CESDI |
| `customtkinter` | Interface gráfica moderna (tema escuro/claro) |
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
