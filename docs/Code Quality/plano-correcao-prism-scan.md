# Plano de Correção — Prism Scan Brain4me

**Data:** 2026-05-29  
**Origem:** `/prism-scan` — relatório de invariantes de estado  
**Referência:** `docs/Code Quality/prism-scan-invariantes.md`

---

## Visão Geral

| # | Severidade | Natureza | Esforço |
|---|---|---|---|
| 1 | HIGH | Corrupção silenciosa de estado (race condition) | Baixo |
| 2 | MEDIUM | Dupla contagem de feedback | Baixo |
| 3 | STRUCTURAL | Score ignorado no search semântico | Médio |
| 4 | STRUCTURAL | LIMIT fixo exclui dados | Médio |
| 5 | STRUCTURAL | Conflação semântica de `last_used_at` | Médio |
| 6 | LOW | Cache stale sem verificação | Baixo |

---

## Fase 1 — Correções Imediatas (HIGH + MEDIUM)

### #1 — Race condition em `store_learned_pattern`

**Arquivo:** `src/brain4me/memory.py`  
**Linhas:** 259-331

**Causa:** SELECT seguido de INSERT/UPDATE fora de controle de concorrência. Dois feedbacks para a mesma `normalized_key` podem ler o mesmo estado e sobrescrever mutuamente.

**Correção:** Envolver a operação em `BEGIN IMMEDIATE` para adquirir lock de escrita no início da transação, prevenindo leituras stale.

```python
def store_learned_pattern(db_path, question, decision, accepted):
    # ... validação inicial ...

    with connect(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")  # ← ADICIONAR
        try:
            # SELECT ... WHERE normalized_key = ?
            # ... lógica de INSERT ou UPDATE ...
            conn.commit()
        except Exception:
            conn.rollback()
            raise
```

**Verificação:** Teste com duas threads disparando `store_learned_pattern` simultaneamente para a mesma `normalized_key`. Assert que `frequency` final = `frequency` inicial + 2.

**Estimativa:** 30 min

---

### #2 — Dupla contagem em `record_feedback`

**Arquivo:** `src/brain4me/feedback.py`  
**Linhas:** 127-133

**Causa:** `if correction:` é um bloco independente, não um `elif` ou `else`. Quando o usuário rejeita com correção, dois `store_learned_pattern` são chamados — um para a decisão original (rejeitada) e outro para a correção (aceita). Mas a decisão original já foi registrada no bloco `if/elif` acima.

**Correção:** Substituir o `if correction:` por `elif correction:` ou reestruturar com `else:`.

```python
if accepted and suggested_decision:
    store_learned_pattern(db_path, question, suggested_decision, True)
elif not accepted and suggested_decision:
    store_learned_pattern(db_path, question, suggested_decision, False)

if correction:
    store_learned_pattern(db_path, question, correction, True)
```

A lógica correta: a correção sempre cria uma entrada separada como `decision_pattern` aceito. O bloco `if/elif` acima registra a decisão original. Esses dois são independentes e corretos — o problema original estava apenas se ambos os branches do `if/elif` disparassem. O código atual já usa `elif`, então a dupla-contagem só ocorreria se `correction` fosse avaliada como verdadeira E `accepted=False` com `suggested_decision` presente — cenário que é válido mas onde a rejeição + correção cria 2 entradas para 1 evento.

**Análise revisada:** Na verdade, rejeitar com correção DEVE criar 2 padrões distintos: o original (rejeitado) e a correção (aceita). Isso é intencional. O overcount real ocorreria se `correction == suggested_decision`, mas isso é extremamente improvável.

**Ação:** Adicionar guard clause para evitar duplicação quando `correction == suggested_decision`:

```python
if correction and normalize_decision_text(correction) != normalize_decision_text(suggested_decision):
    store_learned_pattern(db_path, question, correction, True)
```

**Verificação:** Teste unitário: mock `record_feedback` com `accepted=False` e `correction=suggested_decision`. Assert que apenas 1 `store_learned_pattern` é chamado.

**Estimativa:** 15 min

---

## Fase 2 — Problemas Estruturais

### #3 — `score` armazenado ignorado no search semântico

**Arquivo:** `src/brain4me/query.py`  
**Linhas:** 271-337

**Causa:** `_semantic_context_search` carrega `LIMIT 100` entities por `ORDER BY score DESC`, mas depois re-scorea todas via `semantic_similarity`, descartando o ranking original. O `score` do banco só serve para selecionar quais 100 entram na pool.

**Correção:** Usar o `score` do banco como *prior* no cálculo de similaridade combinada:

```python
combined_score = (semantic_similarity(question, content) * 0.7) + (float(row["score"]) * 0.3)
```

Isso preserva a utilidade do `score` armazenado e evita que entidades com score baixo mas overlap lexical desloquem entidades de alta qualidade.

**Alternativa:** Substituir `LIMIT 100` por uma cláusula `WHERE score >= 0.5` para filtrar low-quality entities antes do search.

**Trade-off:** Aumenta latência marginalmente (multiplicação extra). Mantém retrocompatibilidade.

**Verificação:** Teste com entidade `score=0.95` na posição 101 e entidade `score=0.1` na posição 1. Assert que o ranking final respeita o score.

**Estimativa:** 1h

---

### #4 — LIMITs fixos excluem dados silenciosamente

**Arquivo:** `src/brain4me/query.py`  
**Linhas:** 276 e 284

**Causa:** `LIMIT 100` em entities e `LIMIT 200` em context_nodes são arbitrários. Em bancos com milhares de registros, entidades relevantes podem ser excluídas.

**Correção — duas etapas:**

**4a.** Substituir LIMIT fixo por filtro de qualidade + LIMIT dinâmico:

```python
entity_rows = conn.execute(
    """
    SELECT canonical_name, entity_type, description, score
    FROM entities
    WHERE score >= ?
    ORDER BY score DESC, id
    LIMIT ?
    """,
    (0.3, max(100, int(total_entities * 0.3))),
).fetchall()
```

**4b.** Registrar métrica quando o LIMIT efetivo é atingido e há mais registros disponíveis:

```python
total_entities = conn.execute("SELECT COUNT(*) FROM entities WHERE score >= 0.3").fetchone()[0]
if len(entity_rows) >= limit and total_entities > limit:
    log_metric("semantic_search_truncated", 1.0)
```

**Verificação:** Popular banco com 500+ entities de score > 0.3. Assert que o search semântico retorna resultados das posições 100-200.

**Estimativa:** 1h30

---

### #5 — Conflação semântica de `last_used_at`

**Arquivo:** `src/brain4me/memory.py`  
**Linhas:** 424-425

**Causa:** `last_used_at` é atualizado em toda query que recupera a memória, não apenas em eventos de feedback. `prune_old_memories` usa `last_used_at` para decidir o que arquivar. Patterns antigos mas frequentemente exibidos nunca envelhecem.

**Correção — schema migration:**

**5a.** Adicionar coluna `last_feedbacked_at TEXT` à tabela `memory_entries`:

```python
# Em storage_schema.py, ensure_required_columns:
"memory_entries": {
    # ... colunas existentes ...
    "last_feedbacked_at": "TEXT",
}
```

**5b.** Atualizar `store_learned_pattern` para setar `last_feedbacked_at = now` no INSERT/UPDATE.

**5c.** Atualizar `prune_old_memories` para usar `last_feedbacked_at` em vez de `last_used_at` como critério de idade.

**5d.** Manter `last_used_at` como métrica de exibição (útil para analytics/debug).

**Verificação:** Teste unitário: criar pattern com `last_feedbacked_at` de 200 dias atrás, exibi-lo 5 vezes, assert que `prune_old_memories` o detecta como candidato a arquivamento.

**Estimativa:** 1h30

---

## Fase 3 — Melhoria de Robustez

### #6 — Cache de grafos sem verificação de frescor

**Arquivo:** `src/brain4me/graph_cache.py`

**Causa:** `get_cached_graphs` retorna grafos cacheados sem verificar se o DB foi modificado desde o build.

**Correção:** Adicionar verificação de `mtime` ou `db_hash`:

```python
def get_cached_graphs(db_path):
    db_stat = os.stat(db_path)
    cache_key = (db_stat.st_mtime, db_stat.st_size)

    if _cache and _cache.cache_key == cache_key:
        return _cache

    kg = build_knowledge_graph(db_path)
    cg = build_context_graph(db_path)
    _cache = CachedGraphs(kg=kg, context_graph=cg, cache_hit=False, cache_key=cache_key)
    return _cache
```

**Verificação:** Popular cache, modificar DB via ingest, assert que próxima query reconstrói grafos.

**Estimativa:** 30 min

---

## Ordem de Execução

| Ordem | Item | Severidade | Dependências |
|---|---|---|---|
| 1 | #1 — Race condition `BEGIN IMMEDIATE` | HIGH | Nenhuma |
| 2 | #2 — Guard clause correção duplicada | MEDIUM | Nenhuma |
| 3 | #6 — Cache freshness check | LOW | Nenhuma |
| 4 | #3 — Score como prior no search | STRUCTURAL | Nenhuma |
| 5 | #4 — LIMIT dinâmico + métrica | STRUCTURAL | #3 (mesmo arquivo) |
| 6 | #5 — `last_feedbacked_at` | STRUCTURAL | Schema migration |

## Testes

Cada correção deve incluir:

- **Teste de unidade** específico para o bug corrigido
- **Teste de regressão** cobrindo o caminho feliz pré-existente
- Para itens estruturais (#3, #4, #5): **teste de integração** com dados sintéticos populando o cenário de borda

Arquivos de teste existentes em `tests/`:
- `tests/test_phase6.py` — memory/feedback
- `tests/test_query.py` — search semântico
- `tests/test_schema.py` — schema e migrations

---

## Risco de Regressão

| Item | Risco | Mitigação |
|---|---|---|
| #1 | `BEGIN IMMEDIATE` pode causar deadlock com outras transações | Usar timeout: `BEGIN IMMEDIATE` não bloqueia leituras, só escritas |
| #3 | Mudar fórmula de scoring altera qualidade das respostas | Manter threshold `0.18` inalterado; ajustar pesos (0.7/0.3) após A/B test |
| #5 | Schema migration pode falhar em DBs existentes | `ensure_required_columns` já lida com ALTER TABLE incremental |
