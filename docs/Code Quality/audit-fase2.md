# Auditoria Independente — Fase 2: Correções Estruturais (issues #3, #4, #5)

**Data:** 2026-05-29  
**Escopo:** `src/brain4me/query.py`, `src/brain4me/memory.py`, `src/brain4me/storage_schema.py`  
**Build:** 72/72 testes passando (24.59s)

---

## Issue #3 — Combined Score em `_semantic_context_search`

**Severidade:** HIGH  
**Status:** ✅ CORRETO

| O quê | Onde | Verificação |
|-------|------|-------------|
| `combined_score = similarity*0.7 + score*0.3` | `query.py:299` | Confirmado. Ponderação exata: `(similarity * 0.7) + (float(row["score"]) * 0.3)` |
| Threshold 0.18 aplicado sobre `combined_score` | `query.py:300` | Confirmado. `if combined_score >= threshold:` — usa a variável combinada, não `similarity` pura |
| Campo `score` da entity influencia ranking semântico | `query.py:299,301` | Confirmado. O `score` da entidade entra com peso 0.3 no cálculo e o `combined_score` é usado para ordenação e filtro |

**Nenhum finding.** A implementação corresponde exatamente ao especificado.

---

## Issue #4 — LIMIT Dinâmico + Filtro de Qualidade

**Severidade:** HIGH  
**Status:** ✅ CORRETO

| O quê | Onde | Verificação |
|-------|------|-------------|
| `WHERE score >= 0.3` na query de entities | `query.py:275` | Confirmado. `WHERE score >= 0.3` presente |
| Entity LIMIT aumentado (era 100, agora >= 200) | `query.py:277` | Confirmado. `LIMIT 200` — exatamente 200 |
| Context nodes LIMIT aumentado (era 200, agora >= 500) | `query.py:285` | Confirmado. `LIMIT 500` — exatamente 500 |

**Nenhum finding.** Os limites foram ampliados e o filtro de qualidade `score >= 0.3` está ativo.

---

## Issue #5 — `last_feedbacked_at`

**Severidade:** HIGH  
**Status:** ✅ CORRETO

### Schema (`storage_schema.py`)

| O quê | Linha | Verificação |
|-------|-------|-------------|
| `last_feedbacked_at TEXT` no SCHEMA_SQL (`CREATE TABLE memory_entries`) | ~107 | Presente na definição da tabela |
| `"last_feedbacked_at": "TEXT"` em `ensure_required_columns` | ~131 | Presente no dicionário de colunas obrigatórias para `memory_entries` |

### Leitura e escrita (`memory.py`)

| Função | Linha | Uso | Status |
|--------|-------|-----|--------|
| `_build_pattern_row` | 201 | Leitura do campo do banco: `"last_feedbacked_at": str(_entry_value(entry, "last_feedbacked_at", "") or "")` | ✅ |
| `_write_pattern_row` | 229, 239 | SET do campo no UPDATE SQL: `last_feedbacked_at = ?` | ✅ |
| `store_learned_pattern` (INSERT) | 290, 305 | Seta `"last_feedbacked_at": now` e inclui no INSERT | ✅ |
| `store_learned_pattern` (UPDATE) | 337 | Seta `entry["last_feedbacked_at"] = now` antes de chamar `_write_pattern_row` | ✅ |
| `prune_old_memories` (consolidação) | 500-503 | Usa `max(...)` para preservar o `last_feedbacked_at` mais recente entre duplicatas | ✅ |
| `prune_old_memories` (archiving) | 515-516 | **Campo primário de staleness:** `entry.get("last_feedbacked_at") or entry.get("last_used_at") or entry.get("created_at")` — last_feedbacked_at é o primeiro na cadeia de fallback | ✅ |

### Contagens de ocorrências

```
src/brain4me/memory.py:           12
src/brain4me/storage_schema.py:    2
```

**Nenhum finding.** O campo `last_feedbacked_at` está presente em todos os pontos obrigatórios: schema, migração, leitura, INSERT, UPDATE, consolidação e poda por idade. Em `prune_old_memories` é usado como campo primário de staleness com fallback para `last_used_at` → `created_at`, conforme especificado.

---

## Sumário Final

| Issue | Descrição | Status | Verificação |
|-------|-----------|--------|-------------|
| #3 | Combined score em _semantic_context_search | ✅ CORRETO | Ponderação 0.7/0.3, threshold 0.18 sobre combined_score, score da entity influencia ranking |
| #4 | LIMIT dinâmico + filtro de qualidade | ✅ CORRETO | WHERE score >= 0.3, entity LIMIT=200, context_nodes LIMIT=500 |
| #5 | last_feedbacked_at em schema e queries | ✅ CORRETO | 14 ocorrências totais (schema × 2, memory × 12); presente em CREATE TABLE, ensure_required_columns, _build_pattern_row, _write_pattern_row, store_learned_pattern (INSERT+UPDATE), prune_old_memories (consolidação + archiving com fallback) |

**Build/Test:** 72 passed, 0 failed — estado limpo.

**Conclusão:** As três issues estão implementadas conforme especificado. Nenhum desvio, omissão ou regressão encontrada. A auditoria pode ser considerada **aprovada**.
