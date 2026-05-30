# Prism Scan — Brain4me: Invariantes de Estado e Leis de Conservação

**Data:** 2026-05-29  
**Método:** `/prism-scan` — análise estrutural com lentes cognitivas dinâmicas  
**Foco:** Invariantes de estado e leis de conservação

---

## STEP 0: Prior Constraint Knowledge

Nenhum `.prism-history.md` encontrado — primeira análise prism neste repositório.

## STEP 1: Generated Lens

> Map every piece of state in this system — entities, relations, context_nodes, context_edges, memory_entries, feedback_entries, reasoning_traces. For each, name the operations that mutate it and under what guards. Then trace every mutation path end-to-end: ingestion creates entities; feedback creates memory_entries; memory_entries influence decision ranking. Construct a new system where one of these mutation paths is severed. Predict which state accumulates, which state atrophies, and which invariant breaks silently. Now state the conservation law: what quantity, if not explicitly maintained, MUST be conserved across all valid system states? Derive it from the scoring formulas, the feedback loop, and the dual-graph architecture. Identify the exact code locations where this conservation law is violated or left unenforced. Output a table of silent corruption points — where the system believes state to be consistent but a concurrent operation or missing guard can leave it inconsistent.

## STEP 2: Execute the Lens

### State Inventory & Mutation Paths

| State | Creates | Mutates | Invalidates | Key Guard |
|---|---|---|---|---|
| `entities` | `upsert_entity` (ingest) | — | — | UNIQUE(compartment_id, entity_type, canonical_name) |
| `relations` | `create_relation` (ingest) | — | — | FK → entities |
| `context_nodes` | `create_context_node` (ingest) | — | — | FK → notes |
| `context_edges` | `create_context_edge` (ingest) | — | — | FK → context_nodes |
| `memory_entries` | `store_learned_pattern`, `create_memory_entry` | `_write_pattern_row` (score, frequency, feedback_balance, is_unstable) | `remove_pattern` (valid_to), `prune_old_memories` | `valid_to IS NULL` + `normalized_key` dedup |
| `feedback_entries` | `record_feedback` | — | — | FK → reasoning_traces |
| `reasoning_traces` | `save_reasoning_trace` | — | — | nenhum |
| `knowledge_graph` | `build_knowledge_graph` (full rebuild por query) | — | garbage collected | cache TTL |
| `context_graph` | `build_context_graph` (full rebuild por query) | — | garbage collected | cache TTL |

### The Conservation Law

Há uma quantidade que **deve** ser conservada em todos os estados válidos do sistema mas não é imposta:

> **Para cada `normalized_key` em `memory_entries` ativas, a soma de `frequency` deve igualar o número de `feedback_entries` com `decision_key` correspondente.**

Este é o **invariante de accountability de feedback**. Formalmente:

```
∀ k: Σ frequency(m) = |{ f ∈ feedback_entries | f.decision_key = k }|
  onde m ∈ memory_entries com normalized_key = k e valid_to IS NULL
```

A fórmula de scoring deriva `accepted_count` e `rejected_count` de `frequency` e `feedback_balance`. Se `frequency` se descola dos eventos reais de feedback, todo o sistema de ranqueamento de decisões opera sobre dados corrompidos.

### Violações Encontradas

#### 1. Race condition em `store_learned_pattern` — `memory.py:262-329`

O SELECT-then-UPDATE **não está em uma transação isolada**. Dois feedbacks concorrentes para a mesma decisão:

```
T1: SELECT ... WHERE normalized_key = X → linha R (frequency=5, fb=2)
T2: SELECT ... WHERE normalized_key = X → linha R (frequency=5, fb=2) ← stale
T1: UPDATE frequency=6, fb=3
T2: UPDATE frequency=6, fb=1                          ← sobrescreve T1
```

Um evento de feedback é **silenciosamente perdido**. O `frequency` deveria ser 7 mas fica 6.

**Severidade: HIGH** — viola o invariante de conservação. O sistema acredita ter registrado N eventos quando na verdade registrou N−1.

#### 2. Dupla contagem em `record_feedback` — `feedback.py:127-133`

```python
if accepted and suggested_decision:
    store_learned_pattern(db_path, question, suggested_decision, True)
elif not accepted and suggested_decision:
    store_learned_pattern(db_path, question, suggested_decision, False)

if correction:                                              # ← if separado!
    store_learned_pattern(db_path, question, correction, True)
```

Quando o usuário corrige uma decisão aceita, ambos os branches disparam: a decisão original ganha +1 `frequency`, e a correção ganha sua própria entrada com +1 `frequency`. Dois `memory_entries` para um único evento de feedback.

**Severidade: MEDIUM** — infla o invariante (overcount).

#### 3. `_semantic_context_search` ignora o `score` armazenado — `query.py:271-337`

Entities têm campo `score` populado na ingestão e ordenado `ORDER BY score DESC`. Mas o search semântico carrega `LIMIT 100` entities e re-scorea todas via `semantic_similarity(question, content)`, ignorando completamente o `score` do banco. Uma entidade com `score=0.1` recém-criada pode deslocar uma entidade com `score=0.95` que esteja fora das primeiras 100 linhas.

**Severidade: STRUCTURAL** — o `score` armazenado torna-se irrelevante para queries, minando a premissa de "entidades mais relevantes primeiro".

#### 4. LIMITs fixos no search semântico — `query.py:276-284`

```sql
SELECT ... FROM entities ... LIMIT 100
SELECT ... FROM context_nodes ... LIMIT 200
```

Com o crescimento do banco, entidades e context_nodes fora desses limites são **silenciosamente excluídas** do search semântico. O sistema se torna parcial e não-determinístico sem aviso.

**Severidade: STRUCTURAL** — trade-off performance/semântica que força redesign futuro.

#### 5. `last_used_at` é atualizado em toda query — `memory.py:424-425`

```python
entry["last_used_at"] = now
_write_pattern_row(conn, entry)
```

`prune_old_memories` usa `last_used_at` para arquivar patterns antigos. Mas como toda query que recupera uma memória atualiza `last_used_at`, um pattern com feedback de 6 meses atrás que aparece em queries frequentes **nunca envelhece**. O campo mede "última exibição", não "último feedback relevante".

**Severidade: STRUCTURAL** — conflação semântica. Precisa de `last_feedbacked_at` separado.

#### 6. Cache de grafos sem verificação de integridade — `graph_cache.py`

```python
cached_graphs = get_cached_graphs(db_path)
```

Se o DB é modificado entre o build do cache e o uso (ex: ingest enquanto query roda), o grafo em memória reflete estado stale. Não há hash ou mtime check.

**Severidade: LOW** — improvável em uso single-user, mas possível em cenário multi-processo.

### Tabela de Achados

| # | Local | O que quebra | Severidade | Fixável ou Estrutural |
|---|---|---|---|---|
| 1 | `memory.py:262-329` | Race condition: feedback concorrente perde eventos, viola invariante frequency = \|feedback\| | HIGH | Fixável: `BEGIN IMMEDIATE` |
| 2 | `feedback.py:127-133` | `if` separado para correção cria 2 entradas para 1 evento | MEDIUM | Fixável: `elif` |
| 3 | `query.py:271-337` | `score` armazenado é ignorado pelo search semântico | STRUCTURAL | Estrutural |
| 4 | `query.py:276-284` | LIMIT 100/200 exclui conteúdo silenciosamente | STRUCTURAL | Estrutural |
| 5 | `memory.py:424-425` | `last_used_at` atualizado em query mascara idade real do feedback | STRUCTURAL | Estrutural |
| 6 | `graph_cache.py` | Cache sem verificação de frescor (mtime/hash) | LOW | Fixável |

---

```
CONSTRAINT NOTE: This analysis maximized state invariants, mutation path tracing, and
conservation-law derivation from the scoring formulas and feedback/graph loops.
It did not examine: ingestion pipeline robustness (extractor, linker) or LLM provider
reliability (prompt engineering, degradation modes).
For deeper analysis: /prism-full | For meta-analysis: /prism-reflect
```
