# Fase 1: Suporte a múltiplos formatos de documento (PDF, DOCX, TXT)

## Contexto

Brain4me é um sistema de knowledge graph + suporte à decisão. Atualmente só aceita Markdown com YAML frontmatter via `ingest_markdown_note()`.

## Objetivo

Adicionar suporte a PDF, DOCX e TXT — extrair texto bruto e passar pelo mesmo pipeline de extração de entidades.

## Tarefas

### 1. Adicionar dependências em pyproject.toml

```toml
dependencies = [
  ...
  "pymupdf>=1.24",
  "python-docx>=1.1",
]
```

### 2. Criar src/brain4me/converters.py

Funções:
- `extract_text_from_pdf(path: str | Path) -> str` — usa pymupdf, concatena texto de todas as páginas
- `extract_text_from_docx(path: str | Path) -> str` — usa python-docx, concatena parágrafos
- `extract_text_from_txt(path: str | Path) -> str` — leitura simples, tenta utf-8, fallback latin-1
- `convert_file(path: str | Path) -> str` — router por extensão (.pdf/.docx/.txt), levanta ValueError se formato não suportado

### 3. Adicionar ingest_raw_text() em src/brain4me/ingest.py

Nova função pública:
```python
def ingest_raw_text(
    *,
    db_path: str | Path,
    raw_text: str,
    source_path: str,
    source_type: str,  # "pdf", "docx", "txt"
    compartment: str = "default",
    title: str | None = None,
) -> IngestResult:
```

Esta função:
- Usa `title` passado ou extrai de `Path(source_path).stem`
- Simula um markdown mínimo: cria string "falsified" com metadados para reutilizar `ingest_markdown_note` internamente
- OU extrai o corpo da lógica comum para evitar duplicação

A abordagem mais limpa: refatorar `ingest_markdown_note` para delegar a uma função interna `_ingest_processed_text()` que aceita metadados já processados. Assim ambos os caminhos convergem sem duplicação.

### 4. Adicionar comando CLI em src/brain4me/cli.py

```python
@cli.command("ingest-file")
@click.option("--db", "db_path", default="brain4me.db")
@click.option("--file", "file_path", required=True)
@click.option("--compartment", default="default")
def ingest_file(db_path, file_path, compartment):
    """Ingest a document file (PDF, DOCX, TXT) into Brain4me."""
```

Fluxo:
- Converte arquivo via `convert_file(path)`
- Chama `ingest_raw_text(db_path=db_path, raw_text=text, source_path=file_path, source_type=ext, compartment=compartment)`
- Printa resumo: "Ingested X entities, Y relations, Z warnings"

### 5. Adicionar testes

- `tests/test_converters.py` — testa extração de texto de PDF, DOCX, TXT reais (criar arquivos de exemplo mínimos nos testes)
- `tests/test_ingest_file.py` — testa integração: ingerir PDF/DOCX/TXT e verificar entidades criadas no SQLite

### 6. Atualizar __init__.py

Exportar os símbolos públicos: `convert_file`, `extract_text_from_pdf`, `extract_text_from_docx`, `extract_text_from_txt`, `ingest_raw_text`

## Validação

- `pip install -e ".[dev]"` deve instalar pymupdf e python-docx
- `pytest -x` deve passar todos os testes
- `brain4me ingest-file --file tests/fixtures/sample.pdf` deve funcionar
- `brain4me ingest-file --file tests/fixtures/sample.docx` deve funcionar

## Arquivos-chave existentes

- `/home/petto/brain4me/src/brain4me/ingest.py` — função `ingest_markdown_note()` (linhas 27-130+)
- `/home/petto/brain4me/src/brain4me/extractor.py` — `MarkdownExtractor`, `build_default_extractor()`
- `/home/petto/brain4me/src/brain4me/cli.py` — comandos existentes (`ask`, `ingest`, `explain`, etc.)
- `/home/petto/brain4me/pyproject.toml` — dependências atuais: click, PyYAML, networkx, spacy, streamlit
- `/home/petto/brain4me/src/brain4me/storage.py` — funções SQLite (connect, upsert_entity, create_relation, etc.)
- `/home/petto/brain4me/tests/` — 10 arquivos de teste existentes, usam pytest

## Restrições

- Não quebrar a API existente de `ingest_markdown_note()`
- Manter o estilo de código existente (type hints, docstrings, `from __future__ import annotations`)
- Testes devem criar e limpar bancos temporários
- NÃO usar inline styles em Python (não se aplica aqui — é só Python puro)
