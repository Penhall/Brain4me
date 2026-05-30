# Relatório de Avaliação Técnica — Brain4me MVP
**Data:** 2026-04-29
**Revisão externa:** ChatGPT / avaliador externo
**Branch avaliado:** `main` (bcfcd95)

---

## 1. Resumo Executivo

O Brain4me MVP é um sistema local-first de "segundo cérebro" semântico implementado em Python 3.11+. Foram implementados: pipeline de ingestão de notas Markdown com extração adaptativa de entidades (LLM → spaCy → heurístico), persistência em SQLite com 10 tabelas relacionais, dois grafos NetworkX distintos (Knowledge Graph e Context Graph), mecanismo de entity linking por similitude fuzzy e contextual, sistema de scoring ponderado (recency, frequency, confidence, source reliability), CLI com 11 comandos via Click, e 23 testes automatizados cobrindo os fluxos principais.

O que já funciona: ingestão, extração, linking, scoring, detecção automática de conflitos, construção dos dois grafos, consulta por tópico e entidade, exportação de snapshot em JSON, e o CLI completo. Limitações ainda presentes: o LLM não está integrado no fluxo de consulta (apenas na extração), a resposta ao `brain ask` não cita fontes de forma estruturada, não há mecanismo de expiração de memória, ausência de índices explícitos no banco, e o cliente LLM não tem retry logic.

---

## 2. Estrutura Atual do Projeto

```text
brain4me/
├── pyproject.toml
├── AGENTS.md
├── src/
│   └── brain4me/
│       ├── __init__.py
│       ├── cli.py
│       ├── models.py
│       ├── llm_client.py
│       ├── extractor.py
│       ├── ingest.py
│       ├── ingest_helpers.py
│       ├── linker.py
│       ├── scoring.py
│       ├── storage.py
│       ├── storage_schema.py
│       ├── storage_core.py
│       ├── storage_context.py
│       ├── graphs.py
│       ├── query.py
│       ├── query_helpers.py
│       └── snapshot.py
├── tests/
│   ├── conftest.py
│   ├── test_cli.py
│   ├── test_extractor.py
│   ├── test_ingest.py
│   ├── test_query.py
│   └── test_schema.py
└── docs/
    ├── (32+ arquivos .md de documentação conceitual)
    ├── architecture/
    ├── ontology/
    ├── prompts/
    └── research/
```

---

## 3. Arquivos Criados ou Modificados

| Arquivo | Finalidade | Status |
|---|---|---|
| `src/brain4me/__init__.py` | Exporta IngestResult, TopicExplanation | implementado |
| `src/brain4me/cli.py` | Entry point CLI com 11 comandos Click | implementado |
| `src/brain4me/models.py` | Dataclasses: IngestResult, ExtractionPayload, TopicExplanation, EntityExplanation | implementado |
| `src/brain4me/llm_client.py` | Cliente HTTP OpenAI-compatible via urllib | implementado |
| `src/brain4me/extractor.py` | Adaptive extraction: LLM → spaCy → Heurístico | implementado |
| `src/brain4me/ingest.py` | Pipeline principal de ingestão | implementado |
| `src/brain4me/ingest_helpers.py` | Helpers: frontmatter, conflitos automáticos, attach_context | implementado |
| `src/brain4me/linker.py` | Entity linking fuzzy + contextual | implementado |
| `src/brain4me/scoring.py` | Score ponderado (4 fatores) | implementado |
| `src/brain4me/storage.py` | DB connection wrapper, re-exports | implementado |
| `src/brain4me/storage_schema.py` | DDL SQL das 10 tabelas + ensure_required_columns | implementado |
| `src/brain4me/storage_core.py` | CRUD: compartment, source, note, entity, relation | implementado |
| `src/brain4me/storage_context.py` | CRUD: context_node, context_edge, context_entity_link, memory_entry, ingest_log | implementado |
| `src/brain4me/graphs.py` | build_knowledge_graph / build_context_graph via NetworkX | implementado |
| `src/brain4me/query.py` | explain_topic, ask_question, explain_entity | implementado |
| `src/brain4me/query_helpers.py` | find_decision_rows, fetch_related, fetch_history | implementado |
| `src/brain4me/snapshot.py` | build_snapshot_payload: export completo em JSON | implementado |
| `tests/conftest.py` | Fixtures de notas Markdown e classe base de testes | implementado |
| `tests/test_cli.py` | 11 testes de integração via Click CliRunner | implementado |
| `tests/test_extractor.py` | 4 testes de extração adaptativa | implementado |
| `tests/test_ingest.py` | 7 testes do pipeline de ingestão | implementado |
| `tests/test_query.py` | 7 testes de consulta + grafos | implementado |
| `tests/test_schema.py` | 4 testes de schema e UUID | implementado |
| `pyproject.toml` | Dependências, entry points, Python 3.11+ | implementado |

---

## 4. Banco de Dados

### Schema SQLite — 10 tabelas

**compartments** — Isolamento de domínios
- `id TEXT PRIMARY KEY` (UUID)
- `slug TEXT UNIQUE NOT NULL`
- `name TEXT NOT NULL`
- `description TEXT`
- `created_at TEXT NOT NULL`

**sources** — Rastreabilidade de origem dos documentos
- `id TEXT PRIMARY KEY` (UUID)
- `compartment_id TEXT` → FK compartments(id)
- `source_type TEXT` (personal, external, inferred)
- `source_origin_type TEXT` (adicionado via ensure_required_columns)
- `source_reliability REAL` (0.4–0.9)
- `source_path TEXT`, `hash TEXT` — UNIQUE(source_path, hash)
- `title TEXT`, `captured_at TEXT`

**notes** — Documentos originais
- `id TEXT PRIMARY KEY` (UUID)
- `source_id TEXT` → FK sources(id)
- `content_markdown TEXT`
- `summary TEXT`, `status TEXT`, `created_at TEXT`

**entities** — Conceitos extraídos (nós do Knowledge Graph)
- `id TEXT PRIMARY KEY` (UUID)
- `compartment_id TEXT` → FK compartments(id)
- `entity_type TEXT` — Project, Problem, Decision, Evidence, Alternative, Risk, Objective, Hypothesis, Opportunity
- `canonical_name TEXT`
- `description TEXT`, `confidence REAL`, `score REAL`, `created_at TEXT`
- UNIQUE(compartment_id, entity_type, canonical_name)

**relations** — Arestas do Knowledge Graph
- `id TEXT PRIMARY KEY` (UUID)
- `subject_entity_id TEXT` → FK entities(id)
- `predicate TEXT` — afeta, resolve, supports, alternative_a, warns_about
- `object_entity_id TEXT` → FK entities(id)
- `assertion_type TEXT`, `note_id TEXT`, `confidence REAL`, `score REAL`, `created_at TEXT`

**context_nodes** — Nós do Context Graph
- `id TEXT PRIMARY KEY` (UUID)
- `compartment_id TEXT` → FK compartments(id)
- `node_type TEXT` — decision, evidence, alternative, risk, conflict, exception, inference
- `label TEXT`, `content TEXT`, `note_id TEXT`
- `score REAL`, `created_at TEXT`

**context_edges** — Arestas do Context Graph
- `id TEXT PRIMARY KEY` (UUID)
- `subject_context_node_id TEXT` → FK context_nodes(id)
- `predicate TEXT` — supports, alternative_to, warns_about, contradicts, exception_for, infers
- `object_context_node_id TEXT` → FK context_nodes(id)
- `note_id TEXT`, `created_at TEXT`

**context_entity_links** — Ponte entre Context Graph e Knowledge Graph
- `id TEXT PRIMARY KEY` (UUID)
- `context_node_id TEXT` → FK context_nodes(id)
- `entity_id TEXT` → FK entities(id)
- `role TEXT` — decision, evidence, alternative, risk
- `created_at TEXT`

**memory_entries** — Memória episódica
- `id TEXT PRIMARY KEY` (UUID)
- `compartment_id TEXT` → FK compartments(id)
- `memory_type TEXT` — episodic
- `related_entity_id TEXT` → FK entities(id)
- `content TEXT`, `valid_from TEXT`, `valid_to TEXT` (NULL = ativa)
- `priority REAL`, `score REAL`, `created_at TEXT`

**ingest_logs** — Rastreamento de ingestão
- `id TEXT PRIMARY KEY` (UUID)
- `note_id TEXT`, `source_path TEXT`
- `stage TEXT`, `level TEXT` — warning, error
- `message TEXT`, `created_at TEXT`

### Observações sobre índices

Há `UNIQUE` constraints explícitos em `compartments(slug)`, `sources(source_path, hash)`, e `entities(compartment_id, entity_type, canonical_name)`. **Não há índices explícitos para as queries de LIKE** usadas no fluxo de consulta — ponto de risco em corpora grandes.

### Suporte aos grafos

| Tabela | Knowledge Graph | Context Graph |
|---|---|---|
| entities | ✅ Nós | — |
| relations | ✅ Arestas | — |
| context_nodes | — | ✅ Nós |
| context_edges | — | ✅ Arestas |
| context_entity_links | — | ✅ Ponte para KG |

---

## 5. Knowledge Graph

**Arquivo:** `src/brain4me/graphs.py` — função `build_knowledge_graph(db_path) -> nx.DiGraph`

Usa NetworkX DiGraph. Alimentado pelas tabelas `entities` e `relations`.

**Nós criados:** um nó por entidade, com ID no formato `entity:{id}`, atributos `entity_type` e `label` (canonical_name).

**Arestas criadas:** uma aresta por relação, com atributos `predicate` e `assertion_type`. Arestas direcionadas de `subject_entity_id` para `object_entity_id`.

**Diferenciação de tipo:** o atributo `entity_type` diferencia as entidades (Project, Problem, Decision, Evidence, Alternative, Risk, Objective, Hypothesis, Opportunity). O atributo `predicate` diferencia a semântica das arestas (afeta, resolve, supports, alternative_a, warns_about). Não há nós de "fonte" no grafo — a rastreabilidade de fonte fica nas tabelas `sources` e `notes`, não se materializa como nó do KG.

**Testes:** `test_query.py::test_builds_separate_knowledge_and_context_graphs` verifica que os dois grafos são construídos e que têm nós e arestas distintos.

---

## 6. Context Graph

**Arquivo:** `src/brain4me/graphs.py` — função `build_context_graph(db_path) -> nx.DiGraph`

**É separado do Knowledge Graph:** sim, estruturalmente. São dois `DiGraph` distintos, com namespaces de nós diferentes (`entity:` vs `context:`), alimentados por tabelas distintas, e com predicados diferentes.

**Tabelas:** `context_nodes` (nós) e `context_edges` (arestas).

**Nós criados:** um nó por context_node, ID no formato `context:{id}`, atributos `node_type`, `label`, `content`.

**Arestas criadas:** uma aresta por context_edge, com atributo `predicate` (supports, alternative_to, warns_about, contradicts, exception_for, infers).

**Como decisões, evidências, conflitos e contexto aparecem:**
- Decisões → `node_type=decision`
- Evidências → `node_type=evidence`
- Alternativas → `node_type=alternative`
- Riscos → `node_type=risk`
- Conflitos detectados automaticamente → `node_type=conflict` com aresta `contradicts`
- Exceções → `node_type=exception`
- Inferências → `node_type=inference`

**Ponte KG ↔ Context Graph:** a tabela `context_entity_links` faz a ligação, mas essa ligação **não se materializa como aresta no grafo** — os dois grafos permanecem independentes em memória. A ponte é consultada apenas via SQL no fluxo de query.

**Teste distinção:** `test_query.py::test_builds_separate_knowledge_and_context_graphs` valida que KG e Context Graph são DiGraphs com nomes, nós e arestas distintos.

---

## 7. Scoring e Qualidade de Fonte

**Fórmula implementada em `scoring.py`:**

```
score = 0.25 * recency + 0.20 * frequency + 0.25 * confidence + 0.30 * source_reliability
```

Cada fator é clampado a [0, 1] antes do cálculo. O resultado também é clampado a [0, 1] e arredondado a 4 casas decimais.

**source_reliability** — valores padrão por tipo de fonte:
- `personal`: 0.9
- `external`: 0.6
- `inferred`: 0.4
- `default`: 0.5

**confidence** — campo em `entities` e `relations`, preenchido na extração (LLM retorna valor, heurístico usa valor fixo).

**score** — campo persistido nas tabelas `entities`, `relations`, `context_nodes` e `memory_entries`.

**O que é funcional:**
- ✅ Cálculo de score está implementado e é chamado na ingestão
- ✅ `source_reliability` é derivado do `source_type`/`source_origin_type` do frontmatter
- ✅ Consultas ordenam por `score DESC` (em `find_decision_rows`)
- ✅ Teste `test_ingest_populates_source_quality_and_scores` valida o fluxo

**O que ainda é apenas campo no banco:**
- `recency` na prática é sempre `1.0` (sem cálculo temporal real baseado em data do documento vs. data atual)
- `frequency` é sempre `1.0` na primeira ingestão (não há update ao reingerir o mesmo conteúdo)
- `valid_to` em `memory_entries` é sempre NULL — sem aging

---

## 8. Ingestão

**Pipeline implementado em `ingest.py`, helpers em `ingest_helpers.py`.**

| Capacidade | Status |
|---|---|
| Markdown parser (frontmatter YAML) | ✅ Implementado (`ingest_helpers.split_frontmatter` com PyYAML) |
| Extractor adaptativo | ✅ Implementado (LLM → spaCy → Heurístico) |
| Extractor usa LLM | ✅ Opcional via variáveis de ambiente |
| Extractor usa heurística | ✅ Regex + label mapping PT |
| Extractor usa spaCy | ✅ Fallback com `pt_core_news_sm` |
| Fallback para JSON inválido | ✅ `_repair_json_document` (trailing commas, aspas unicode) + fallback heurístico |
| Checksum SHA256 | ✅ `hashlib.sha256` do conteúdo completo |
| Transação no banco | Parcial — SQLite auto-commit por operação; sem `BEGIN/COMMIT` explícito no pipeline |
| Linker de entidades duplicadas | ✅ `linker.find_linked_entity_id` (fuzzy + contextual) |
| Geração de contexto automática | ✅ `create_automatic_conflicts`, `attach_context_items` |
| Memória episódica automática | ✅ Criada para cada decisão ingerida |

**Observação crítica sobre transações:** cada operação de INSERT é executada individualmente sem um `BEGIN` explícito envolvendo todo o pipeline de ingestão. Uma falha parcial pode deixar o banco em estado inconsistente (source criada sem entities, por exemplo).

---

## 9. Consulta

**Implementado em `query.py` e `query_helpers.py`.**

| Capacidade | Status |
|---|---|
| `brain ask` existe | ✅ Mapeado para `ask_question()` |
| Recuperação de entidades | ✅ LIKE pattern por canonical_name e content de context_nodes |
| Montagem de subgrafo | Parcial — retorna listas estruturadas (TopicExplanation), não subgrafo NetworkX diretamente |
| Ranqueamento por contexto | ✅ `find_decision_rows` ordena por `score DESC` |
| Resposta cita fontes | Não — retorna labels/content sem referência a source_path ou title |
| LLM integrado na consulta | ❌ Não — a resposta é assemblada por Python puro; o LLM não é chamado no fluxo de query |

O fluxo de consulta atual é um **retrieval estruturado**: encontra decisões via SQL LIKE, busca evidências/alternativas/riscos associados, e retorna como struct `TopicExplanation`. Não há geração de resposta em linguagem natural pelo LLM.

---

## 10. CLI

| Comando | Status | Observação |
|---|---|---|
| `brain ingest` | ✅ implementado | Ingere arquivo Markdown com extração adaptativa |
| `brain ask` | ✅ implementado | Retrieval estruturado; sem LLM na resposta |
| `brain explain` | ✅ implementado | Dois modos: `--topic` e `--entity` |
| `brain decide` | ✅ implementado | Registra decisão estruturada com alternativas e riscos |
| `brain log` | ✅ implementado | Registra evento como nota livre |
| `brain fact` | ✅ implementado | Registra fato manual |
| `brain summary` | ✅ implementado | Contagem de entidades e grafos (equivale a "brain review") |
| `brain export` | ✅ implementado | Snapshot completo em JSON |
| `brain review decisions` | ❌ pendente | Não há subcomando `review` com filtro por tipo |
| `brain memory episodes` | ❌ pendente | Não há subcomando `memory` |
| `brain memory patterns` | ❌ pendente | Não há subcomando `memory` |
| `brain curate` | ❌ pendente | Não implementado |

---

## 11. Testes

| Arquivo | O que valida | Tipo | Como executar | Status |
|---|---|---|---|---|
| `tests/test_schema.py` | Criação das 10 tabelas, colunas UUID, score/reliability | Unitário (DB) | `pytest tests/test_schema.py` | ✅ 4 testes |
| `tests/test_extractor.py` | Prioridade LLM, fallback spaCy, recovery JSON inválido, fenced JSON | Unitário (mock) | `pytest tests/test_extractor.py` | ✅ 4 testes |
| `tests/test_ingest.py` | Pipeline completo, labels naturais, freeform, scoring, entity linking, linking semântico | Integração (DB real) | `pytest tests/test_ingest.py` | ✅ 7 testes |
| `tests/test_query.py` | explain_topic, grafos separados, busca por contexto/projeto/problema, ranking por score, conflito entre decisões | Integração (DB real) | `pytest tests/test_query.py` | ✅ 8 testes |
| `tests/test_cli.py` | Fluxo completo via CLI, JSON output, decide, fact, log, export, summary | Integração (CLI) | `pytest tests/test_cli.py` | ✅ 11 testes |

**Total: 34 testes** (soma real considerando test_query com 8 métodos).

**Suíte completa:** `pytest tests/`

**Lacunas de cobertura:**
- Não há teste isolado de `linker.py` (coberto indiretamente via `test_ingest`)
- Não há teste de `scoring.py` diretamente
- Não há teste de `snapshot.py` isolado (coberto via CLI export)
- Não há teste de falha de transação / rollback
- Não há teste de LLM client com falha de rede

---

## 12. Decisões Técnicas Tomadas

| Decisão | Motivo | Trade-off |
|---|---|---|
| SQLite como banco único | Local-first, sem dependências externas, portabilidade | Sem suporte nativo a full-text search eficiente; LIKE queries escalam mal |
| Dois grafos NetworkX separados (KG + CG) | Separação semântica: KG = conhecimento atemporal, CG = raciocínio contextual | Os grafos são reconstruídos a cada chamada a partir do banco; sem persistência em memória |
| Adaptive extractor (LLM → spaCy → heurístico) | Permite funcionar offline, degradar graciosamente sem LLM | Heurístico pode ser impreciso para textos livres complexos |
| Cliente LLM via urllib (sem SDK) | Zero dependências extras, compatível com qualquer provedor OpenAI-compatible | Sem retry, streaming, ou circuit breaker |
| Entity linking fuzzy (Jaccard + SequenceMatcher) | Evitar duplicação de entidades com variações textuais | Falsos positivos possíveis para nomes curtos; threshold 72% pode ser alto/baixo para diferentes domínios |
| UUIDs como TEXT (não INTEGER) | Ids estáveis, não sequenciais, portáveis | Joins ligeiramente mais lentos que INTEGER PK |
| Scoring ponderado com 4 fatores | Permite priorização multidimensional de evidências | recency e frequency não são calculados dinamicamente ainda |
| Frontmatter YAML para metadados | Padrão familiar, human-readable, extensível | Exige formatação correta; YAML tem edge cases perigosos (yaml.safe_load mitiga) |
| `ensure_required_columns` para migrações | Permite adicionar colunas sem recriar o banco | Não é um sistema de migração real; não há rollback, versioning ou down-migrations |
| `ON DELETE` não declarado | Simplifica o schema | Registros órfãos possíveis se entidades forem removidas manualmente |

---

## 13. Lacunas Conhecidas

### Crítico

- **Sem transação explícita no pipeline de ingestão:** uma falha parcial (ex: erro ao criar context_nodes após criar entities) deixa o banco inconsistente. Falta um `BEGIN/COMMIT` envolvendo todo o `ingest_markdown_note`.
- **LLM ausente no fluxo de consulta:** `brain ask` retorna retrieval estruturado sem síntese em linguagem natural. A pergunta do usuário não gera resposta contextualizada.
- **Sem citação de fontes na resposta:** `TopicExplanation` não carrega `source_path`, `title` ou `captured_at`. O usuário não sabe de onde vem cada evidência.
- **`brain review decisions`, `brain memory`, `brain curate` não implementados:** comandos previstos no contrato do CLI estão ausentes.

### Importante

- **recency e frequency não são calculados dinamicamente:** ambos retornam `1.0` por padrão. O score não reflete a passagem do tempo nem a frequência real de menção.
- **Sem índices explícitos para queries LIKE:** `find_decision_rows` usa `LIKE '%term%'` em `canonical_name` e `content`. Sem índice, a query faz full scan. Inviável com centenas de notas.
- **Sem mecanismo de expiração de memória:** `memory_entries.valid_to` é sempre NULL. Memória episódica nunca expira ou é superada.
- **Sem paginação em `snapshot.py`:** `_fetch_table_rows` faz `SELECT *` sem `LIMIT`. Exportações de corpora grandes podem esgotar memória.
- **Sem retry no cliente LLM:** timeout fixo de 30s, sem reprocessamento em falhas de rede.
- **Grafos reconstruídos a cada chamada:** `build_knowledge_graph` e `build_context_graph` fazem `SELECT *` e constroem o grafo do zero. Sem cache.

### Futuro

- `memory_type` fixado em `episodic` — memória semântica e procedimental não estão modeladas.
- Sem suporte a múltiplos compartments via CLI (o compartment é derivado do frontmatter, mas a CLI não tem um seletor explícito).
- Sem API REST ou interface web.
- Sem suporte a embeddings vetoriais para busca semântica densa.
- Sem mecanismo de curadoria/aprovação de entidades extraídas automaticamente.
- spaCy model `pt_core_news_sm` deve ser instalado separadamente; sem fallback documentado se ausente.

---

## 14. Riscos Arquiteturais

**Acoplamento excessivo:** moderado. `ingest.py` chama `storage_core`, `storage_context`, `linker`, `scoring`, `ingest_helpers` diretamente. Uma mudança de schema exige atualizar múltiplos módulos. Não há camada de repositório ou porta de abstração.

**Schema frágil:** `ensure_required_columns` é um mecanismo de migração ad hoc sem versioning. Colunas são adicionadas via `ALTER TABLE ADD COLUMN`; não há suporte a renomear colunas, remover colunas, ou alterar tipos. Em produção, isso escala mal.

**Context Graph virando tabela auxiliar:** risco real. A separação entre KG e Context Graph existe nos grafos NetworkX, mas na consulta (`query_helpers.py`) ambos são consultados via SQL puro, sem passar pelos objetos de grafo. O NetworkX é usado apenas na exportação/snapshot. Se o padrão continuar, o Context Graph pode perder identidade arquitetural e se tornar apenas mais tabelas.

**Duplicação de entidades:** o linker tem threshold fixo (72%) e stopwords hardcoded em PT. Para domínios técnicos com siglas curtas (ex: "DB", "KG", "API"), o threshold pode ser muito alto e não vincular variantes. Para domínios com termos genéricos, pode ser muito baixo.

**Falta de rastreabilidade na resposta:** o fluxo de consulta não rastreia de qual source veio cada evidência retornada. O usuário não pode verificar a origem de uma resposta — contradiz o princípio de "second brain" auditável.

**Excesso de dependência do LLM (na extração):** se o LLM produzir JSON malformado ou entidades erradas, o sistema aceita silenciosamente (fallback heurístico). Não há mecanismo de validação pós-extração ou curadoria humana antes de persistir.

**Testes insuficientes para falhas:** todos os 34 testes cobrem o caminho feliz (happy path). Não há testes para: falha de rede no LLM, hash duplicado na ingestão, banco corrompido, frontmatter inválido, nota sem body, entidade com nome vazio.

---

## 15. Próximos Passos Recomendados

Em ordem de prioridade:

1. **Envolver pipeline de ingestão em transação explícita** — `BEGIN IMMEDIATE / COMMIT / ROLLBACK` em `ingest_markdown_note`. Crítico para consistência.

2. **Integrar LLM no fluxo de consulta** — `ask_question` deve sintetizar resposta em linguagem natural a partir do subgrafo recuperado, com citação de fontes (source_path + title).

3. **Implementar citação de fontes** — `TopicExplanation` e `EntityExplanation` devem carregar metadados de source para cada item retornado.

4. **Adicionar índices no banco** — índices em `entities(canonical_name)`, `context_nodes(content)`, `context_nodes(node_type)` para suportar as queries LIKE em escala.

5. **Calcular recency dinamicamente** — usar `captured_at` da source vs. data atual para computar decaimento temporal no score.

6. **Implementar `brain memory`** — subcomandos `episodes` e `patterns` consultando `memory_entries` com filtros por tipo e período.

7. **Implementar `brain review decisions`** — listagem de decisões com filtro por compartment, período e score mínimo.

8. **Substituir `ensure_required_columns` por sistema de migração** — adoptar Alembic ou um sistema simples de versioning de schema com tabela `schema_version`.

9. **Adicionar paginação em snapshot/export** — `LIMIT/OFFSET` em `_fetch_table_rows` ou streaming JSON para corpora grandes.

10. **Testes de falha** — cobrir: JSON malformado, rede LLM indisponível, frontmatter inválido, nota duplicada, banco bloqueado.

11. **Implementar `brain curate`** — interface para revisar e aprovar/rejeitar entidades extraídas automaticamente antes de consolidá-las no Knowledge Graph.

12. **Cache de grafos em memória** — evitar reconstrução completa dos grafos a cada consulta; invalidar cache na ingestão.

---

*Relatório gerado por avaliação automatizada do repositório em `main` (bcfcd95). Não foram alterados arquivos do projeto.*
