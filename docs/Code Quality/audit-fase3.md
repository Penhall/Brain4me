# Auditoria Independente — Fase 3: Cache Freshness (issue #6)

**Data:** 2026-05-29  
**Escopo:** `src/brain4me/graph_cache.py`  
**Build:** 72/72 testes passando (24.53s)

---

## Issue #6 — Cache Freshness: cache_key, TTL, invalidate_cache

**Severidade:** HIGH  
**Status:** ✅ CORRETO

### 1. `cache_key` com `st_mtime`

| O quê | Onde | Verificação |
|-------|------|-------------|
| `cache_key = (db_stat.st_mtime, db_stat.st_size)` | `load_graphs():56-57` | Confirmado. Tupla com timestamp de modificação + tamanho do arquivo |
| `cache_key = (db_stat.st_mtime, db_stat.st_size)` | `get_cached_graphs():71` | Confirmado. Recalculado a cada acesso |
| Comparação com cache armazenado | `get_cached_graphs():76` | Confirmado. `cache.cache_key == cache_key` — qualquer mudança em mtime ou size força reload |

O `st_mtime` captura o timestamp Unix de modificação do arquivo SQLite. O `st_size` funciona como hash auxiliar contra colisões de timestamp (dois salvamentos no mesmo segundo com tamanhos diferentes são detectados). A comparação é feita antes de qualquer decisão de cache-hit.

### 2. TTL (Time-To-Live)

| O quê | Onde | Verificação |
|-------|------|-------------|
| `ttl_seconds: int = 60` no dataclass | `GraphCache:35` | Confirmado. Default 60s no modelo |
| `cache_age_within_ttl = ... (now - last_loaded_at) <= ttl_seconds` | `get_cached_graphs():73` | Confirmado. Idade do cache calculada contra `time()` atual |
| TTL propagado para o cache após reload | `get_cached_graphs():79,92` | Confirmado. `cache.ttl_seconds = ttl_seconds` em ambos os paths |
| Três condições no short-circuit | `get_cached_graphs():75-80` | Confirmado. **Todas** devem ser verdade: (a) cache completo, (b) `cache_key` inalterado, (c) idade dentro do TTL |

A lógica de expiry é correta: mesmo que o `cache_key` bata, se o cache envelheceu além do TTL, ele é recarregado. Isso protege contra cenários onde o arquivo não mudou mas o processo espera dados frescos (ex.: ingestão externa concorrente).

### 3. `invalidate_cache()`

| O quê | Onde | Verificação |
|-------|------|-------------|
| Invalidação global (`db_path is None`) | `invalidate_cache():99-100` | Confirmado. `_GRAPH_CACHES.clear()` |
| Invalidação por path específico | `invalidate_cache():102` | Confirmado. `_GRAPH_CACHES.pop(_normalize_db_path(db_path), None)` |
| Chamada a partir de `ingest.py` | `ingest.py:7` | Confirmado. `from .graph_cache import invalidate_cache` |
| `get_cache_snapshot()` para diagnóstico | `graph_cache.py:105-130` | Confirmado. Exporta estado do cache para CLI/metrics |

A invalidação é chamada em `ingest_markdown_note` sempre que uma nova nota é ingerida, garantindo que grafos subsequentes refletem o banco atualizado.

### 4. Cache Hit Tracking

| O quê | Onde | Verificação |
|-------|------|-------------|
| `cache.cache_hit = True` no short-circuit | `get_cached_graphs():77` | Confirmado. Hit verdadeiro |
| `cache_hit` condicional no reload | `get_cached_graphs():87-91` | Confirmado. Marca como hit mesmo após reload se o conteúdo dos grafos for idêntico ao anterior (caso de "save sem mudança real") |
| `log_metric("graph_cache_hit", ...)` | `get_cached_graphs():80,93` | Confirmado. Métrica registrada em ambos os paths |
| `log_metric("graph_cache_age_seconds", ...)` | `get_cached_graphs():81,94` | Confirmado. Idade real do cache servido no hit, 0.0 no reload |

### 5. Observações de Baixa Severidade

**Nenhum finding HIGH.** Duas observações documentadas abaixo para referência futura:

- **Precisão de `st_mtime`:** Em alguns filesystems (ex.: ext4 com `noatime`), `st_mtime` tem granularidade de segundos. Se o banco for modificado duas vezes no mesmo segundo, com mesmo tamanho final, o `cache_key` colidiria. Impacto prático mínimo — cenário raro e a diferença de conteúdo seria capturada no próximo TTL expiry. Mitigação natural: `st_size` entra como segundo componente.

- **Race window teórica:** Entre `os.stat()` (linha 70) e o uso do cache (linha 76), o arquivo poderia ser modificado externamente. O `cache_key` armazenado (da chamada anterior) ainda difere do recém-calculado se houve mudança, então o reload é forçado corretamente. Não há janela de dados inconsistentes.

### 6. Testes

O teste `test_graph_cache_reuses_graphs_until_invalidation` em `tests/test_phase6.py:26-46` cobre:

1. **Reuso:** `get_cached_graphs()` chamado duas vezes — mesmo objeto `kg` retornado (linha 37)
2. **Cache hit flag:** `second.cache_hit == True` (linha 38)
3. **TTL expiry:** `last_loaded_at` retrocedido em 120s → reload forçado, objeto diferente (linhas 40-42)
4. **Invalidação explícita:** `invalidate_cache(db_path)` → próxima chamada retorna novo objeto (linhas 44-46)

---

## Sumário Final

| Item | Descrição | Status | Verificação |
|------|-----------|--------|-------------|
| cache_key com st_mtime | Tupla `(st_mtime, st_size)` em load e get | ✅ CORRETO | Comparação exata antes do short-circuit |
| TTL | Default 60s, verificado em `get_cached_graphs()` | ✅ CORRETO | Três condições lógicas (completo + key match + idade ≤ TTL) |
| invalidate_cache | Global e por path, chamado na ingestão | ✅ CORRETO | `clear()` e `pop()` — sem vazamento de memória |
| Cache hit tracking | Flag + métricas em ambos os paths | ✅ CORRETO | Inclui detecção de "conteúdo idêntico após reload" |
| Testes | 72/72 passando | ✅ LIMPO | `test_graph_cache_reuses_graphs_until_invalidation` cobre reuso, TTL expiry e invalidação |

**Build/Test:** 72 passed, 0 failed — estado limpo.

**Conclusão:** A implementação de cache freshness em `graph_cache.py` está completa e correta. O `cache_key` usa `st_mtime` e `st_size`, o TTL é respeitado com granularidade de segundos, e `invalidate_cache` é chamada no ponto correto (após ingestão). Nenhum desvio, omissão ou regressão encontrada. As duas observações de baixa severidade não representam risco operacional. A auditoria pode ser considerada **aprovada**.
