# Plano: Brain4me Multimodal + Visualização + Electron

Data: 2026-05-30
Objetivo: Adicionar suporte a PDF/DOCX/TXT, visualização de grafo interativo (estilo InfraNodus), e app Electron desktop.

---

## Arquitetura atual do Brain4me

```
Markdown c/ frontmatter → ingest_markdown_note() → MarkdownExtractor.extract(body)
                                                         ↓
                                              Entidades (Decision, Risk, Evidence…)
                                              + Relações (afeta, resolve, supports…)
                                                         ↓
                                              SQLite (9 tabelas) → GraphCache (NetworkX)
                                                         ↓
                                              ask_question() → QueryResult → Streamlit app.py
```

**Pipeline de ingestão:** `ingest.py::ingest_markdown_note()` — aceita `markdown_text`, extrai frontmatter YAML, passa `body` para `extractor.extract()`, cria entidades/relações no SQLite.

**Grafo:** `graphs.py` constrói 2 `nx.DiGraph` a partir do SQLite. `graph_cache.py` mantém cache em memória com TTL 60s.

**App Streamlit:** `app.py` — 217 linhas, sem gráficos visuais. Sidebar mostra estatísticas e histórico, área principal mostra Q&A textual.

---

## Fase 1: Formatos de documento (PDF, DOCX, TXT)

### O que fazer

1. **Novas dependências** em `pyproject.toml`:
   - `pymupdf` (PDF)
   - `python-docx` (DOCX)

2. **Novo módulo** `src/brain4me/converters.py`:
   - `extract_text_from_pdf(path: Path) -> str` — PyMuPDF, concatena páginas
   - `extract_text_from_docx(path: Path) -> str` — python-docx, concatena parágrafos
   - `extract_text_from_txt(path: Path) -> str` — leitura simples com charset detection
   - `convert_file(path: Path) -> str` — router por extensão

3. **Nova função** `ingest_raw_text()` em `ingest.py`:
   - Aceita texto puro (sem frontmatter) + metadados (source_path, source_type, compartment, title)
   - Delega para o mesmo pipeline do `ingest_markdown_note()` internamente
   - Source type: "pdf", "docx", "txt"

4. **Novo comando CLI** `brain4me ingest-file`:
   - `brain4me ingest-file --db /path/to/db --file doc.pdf --compartment projetos`
   - Detecta tipo por extensão → converte → ingere

5. **Testes** (~10 novos testes):
   - `test_converters.py` — conversão de PDF, DOCX, TXT de exemplo
   - `test_ingest_file.py` — integração de ingestão de arquivos

### Arquivos a modificar/criar

| Arquivo | Ação | Descrição |
|---|---|---|
| `pyproject.toml` | modificar | Adicionar pymupdf, python-docx |
| `src/brain4me/converters.py` | criar | ~80 linhas, 4 funções |
| `src/brain4me/ingest.py` | modificar | Adicionar `ingest_raw_text()` (~30 linhas) |
| `src/brain4me/cli.py` | modificar | Adicionar comando `ingest-file` (~40 linhas) |
| `src/brain4me/__init__.py` | modificar | Exportar novos símbolos públicos |
| `tests/test_converters.py` | criar | Testes de conversão |
| `tests/test_ingest_file.py` | criar | Testes de integração |
| `docs/plans/phase-multimodal-viz-electron.md` | manter | Este arquivo |

---

## Fase 2: Visualização de grafo (estilo InfraNodus)

### O que fazer

1. **Novo módulo** `src/brain4me/graph_viz.py`:
   - `build_graph_html(cache: GraphCache, highlight_entities: list[str] | None = None) -> str`
   - Converte `cache.kg` (NetworkX) → JSON → HTML com Sigma.js embedado
   - Sigma.js v2 via CDN (sem novas deps Python)
   - Layout ForceAtlas2, nós coloridos por `entity_type`, arestas rotuladas por `predicate`
   - Highlight opcional: destaca subgrafo relevante à query atual

2. **Modificação em `app.py`**:
   - Nova tab "Grafo do Conhecimento" abaixo da resposta
   - Renderiza grafo via `st.components.v1.html(build_graph_html(cache))`
   - Ao fazer uma query, passa entidades detectadas para highlight

3. **Paleta de cores por tipo**:

   | Entity Type | Cor |
   |---|---|
   | Decision | `#ef4444` (vermelho) |
   | Problem | `#f59e0b` (laranja) |
   | Evidence | `#3b82f6` (azul) |
   | Risk | `#ef4444` (vermelho escuro) |
   | Alternative | `#8b5cf6` (roxo) |
   | Hypothesis | `#ec4899` (rosa) |
   | Objective | `#10b981` (verde) |
   | Opportunity | `#22c55e` (verde claro) |
   | Project | `#6366f1` (indigo) |

### Arquivos a modificar/criar

| Arquivo | Ação | Descrição |
|---|---|---|
| `src/brain4me/graph_viz.py` | criar | ~100 linhas, função de renderização |
| `app.py` | modificar | Adicionar tab de grafo (~40 linhas) |
| `src/brain4me/__init__.py` | modificar | Exportar `build_graph_html` |

### Design da visualização

- Sigma.js v2 via CDN: `https://cdn.jsdelivr.net/npm/sigma@2/build/sigma.min.js`
- Layout: ForceAtlas2 via `graphology-forceatlas2`
- Interações: zoom (scroll), pan (drag), hover (highlight vizinhos), clique (tooltip com label + tipo)
- Tamanho do nó: proporcional a `score`
- Espessura da aresta: proporcional a `score`
- Cor do nó: mapeada por `entity_type`
- Background: `#0e1117` (dark, como Streamlit tema escuro)

---

## Fase 3: Electron Desktop App

### O que fazer

Criar um projeto Electron separado em `/home/petto/brain4me/electron/` — **não** dentro do pacote Python.

1. **Estrutura do projeto Electron:**

```
electron/
├── package.json
├── main.js           # Processo principal (~200 linhas)
├── preload.js        # Context bridge (~30 linhas)
├── renderer.js       # UI da janela principal (~150 linhas)
├── index.html        # HTML da janela
├── styles.css        # Pico CSS + custom
├── assets/
│   └── icon.png
└── README.md
```

2. **Funcionalidades:**

   - **File picker nativo** — selecionar PDF/DOCX/TXT/MD para ingestão
   - **Auto-ingestão** — ao selecionar arquivos, executa `brain4me ingest-file --db <path> --file <path>` via `child_process.exec`
   - **Configuração** — campo para db_path do Brain4me (persistido em `electron-store`)
   - **Status** — mostra última ingestão, contagem de entidades (via `brain4me metrics`)
   - **System tray** — ícone na bandeja com menu rápido

3. **Dependências:**

   - `electron` 35+
   - `electron-store` (persistência)
   - Nenhum framework UI — vanilla HTML/JS como o Khoj faz

4. **Fluxo:**

   ```
   Usuário clica "Add Files" → native dialog → seleciona PDFs/DOCXs
   → Electron lê db_path do config → executa brain4me ingest-file para cada
   → Mostra progresso → atualiza status com contagem de entidades
   ```

### Arquivos a criar

| Arquivo | Descrição |
|---|---|
| `electron/package.json` | Dependências e scripts |
| `electron/main.js` | Processo principal, IPC handlers |
| `electron/preload.js` | Context bridge seguro |
| `electron/renderer.js` | UI lógica |
| `electron/index.html` | HTML da janela principal |
| `electron/styles.css` | Estilos (Pico CSS) |
| `electron/README.md` | Docs de build e uso |
| `electron/.gitignore` | node_modules, dist, out |

---

## Ordem de execução

As 3 fases são independentes — podem rodar em paralelo.

**Fase 1 (Formatos):** Codex / CodeWhale — Python puro, bem definido
**Fase 2 (Visualização):** CodeWhale — Python + JS embedado, requer cuidado com Sigma.js
**Fase 3 (Electron):** CodeWhale — JS/Node, projeto separado

---

## Critérios de aceitação

- [ ] `brain4me ingest-file --file doc.pdf` funciona e cria entidades no SQLite
- [ ] `brain4me ingest-file --file doc.docx` funciona
- [ ] `brain4me ingest-file --file notes.txt` funciona
- [ ] Todos os testes passam (`pytest -x`)
- [ ] App Streamlit mostra grafo interativo abaixo da resposta
- [ ] Grafo tem nós coloridos por tipo, arestas rotuladas
- [ ] Highlight funciona ao fazer query
- [ ] Electron app compila (`npm run build` bem-sucedido)
- [ ] Electron app abre, seleciona arquivos, executa ingestão
- [ ] Documentação atualizada nos arquivos README/docs relevantes
