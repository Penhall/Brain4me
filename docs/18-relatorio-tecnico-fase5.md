# Relatório Técnico — Brain4me · Fase 5
**Data:** 2026-05-01
**Branch avaliado:** `main`
**Commit base:** `310227c`

---

## 1. Resumo Executivo

A Fase 5 endureceu o sistema de aprendizado do Brain4me para evitar degradação por uso contínuo. O foco desta etapa não foi adicionar uma feature nova de produto, mas controlar como padrões aprendidos são consolidados, ranqueados, penalizados e governados.

O sistema agora:

- calcula score evolutivo de memória dinamicamente;
- penaliza decisões rejeitadas repetidamente;
- agrupa padrões equivalentes por normalização textual;
- descarta padrões instáveis do contexto operacional;
- expõe governança manual via CLI e UI;
- explica explicitamente o aprendizado por trás da recomendação.

**Status de verificação:** `65 testes passando`.

---

## 2. Escopo Entregue

### Implementado nesta fase

- score evolutivo de memória com frequência, confiança, recência e saldo de feedback;
- penalização forte para padrões rejeitados e instáveis;
- normalização de texto de decisão para evitar duplicação superficial;
- governança de padrões com listagem, remoção e revisão;
- explicação explícita de aprendizado no recommendation path;
- proteção contra feedback inconsistente;
- painel de aprendizado do sistema na UI;
- testes dedicados para score, penalização, instabilidade, governança e impacto na decisão.

### Mantido sem ruptura

- arquitetura geral do pipeline;
- tabelas existentes do MVP;
- fluxo de ingestão;
- explainers e query flow das fases 3 e 4;
- sistema de feedback e trace da Fase 4;
- compatibilidade da suíte completa.

---

## 3. Fluxo Atual de Aprendizado Controlado

O aprendizado agora opera em dois níveis:

### Fluxo de resposta

```text
question
→ retrieval por grafo
→ memória relevante
→ filtro de padrões estáveis
→ contexto enriquecido
→ decisão sugerida com penalização
→ resposta
```

### Fluxo de aprendizado

```text
feedback
→ normalização do padrão
→ atualização de frequência / confiança / saldo
→ detecção de instabilidade
→ recálculo de score
→ influência nas próximas respostas
```

Na prática, o sistema deixa de “aprender tudo” e passa a aprender com controle explícito.

---

## 4. Arquivos Criados e Alterados

### Novos arquivos

| Arquivo | Responsabilidade |
|---|---|
| `src/brain4me/patterns.py` | normalização de texto de decisão |
| `src/brain4me/memory_governance.py` | listagem, remoção e ajuste manual de padrões |
| `tests/test_phase5.py` | cobertura da Fase 5 |
| `docs/superpowers/plans/2026-05-01-fase-5-controle-aprendizado.md` | plano da fase |

### Arquivos alterados

| Arquivo | Mudança principal |
|---|---|
| `src/brain4me/storage_schema.py` | colunas adicionais leves em `memory_entries` e `feedback_entries` |
| `src/brain4me/memory.py` | score evolutivo, penalização, consolidação e filtro de memória |
| `src/brain4me/feedback.py` | detecção de padrões instáveis e marcação protetiva |
| `src/brain4me/decision_engine.py` | ranqueamento por aprendizado, penalização e explicação explícita |
| `src/brain4me/cli.py` | comandos `brain memory list`, `brain memory remove`, `brain memory review` |
| `app.py` | painel de aprendizado, buckets de padrões e remoção manual |

---

## 5. Componentes Técnicos

### 5.1 Score Evolutivo de Memória

**Arquivo:** `src/brain4me/memory.py`

Função implementada:

```python
def compute_memory_score(entry) -> float:
```

Fórmula aplicada:

```text
score = (
  (frequency * 0.4) +
  (confidence_score * 0.3) +
  (recency_weight * 0.2) +
  (feedback_balance * 0.1)
)
```

Detalhes de implementação:

- `frequency` é normalizada em faixa útil;
- `confidence_score` é clampado entre `0` e `1`;
- `recency_weight` é calculado dinamicamente a partir de `last_used_at` ou `created_at`;
- `feedback_balance` entra como componente positivo ou negativo;
- padrões instáveis sofrem redução adicional do score.

### 5.2 Penalização de Decisões Rejeitadas

**Arquivo:** `src/brain4me/memory.py`

Função implementada:

```python
def apply_feedback_penalty(decision: str, memories) -> float:
```

Comportamento:

- rejeições repetidas sem aceitação derrubam a influência drasticamente;
- padrões instáveis recebem penalização mais dura;
- decisões com rejeições recorrentes deixam de ser priorizadas.

Essa penalização é usada no cálculo final de influência e no ranking do decision engine.

### 5.3 Agrupamento Semântico Superficial

**Arquivo:** `src/brain4me/patterns.py`

Função implementada:

```python
def normalize_decision_text(text: str) -> str:
```

Ela:

- remove acentos;
- normaliza caixa;
- remove ruído superficial;
- aplica substituições simples de termos equivalentes, como `manter` → `usar`.

Objetivo:

- consolidar padrões semanticamente equivalentes sem embeddings;
- evitar duplicação por pequenas variações textuais.

### 5.4 Proteção contra Aprendizado Ruim

**Arquivo:** `src/brain4me/feedback.py`

Função implementada:

```python
def detect_unstable_pattern(pattern) -> bool:
```

Critérios atuais de instabilidade:

- múltiplas correções diferentes para o mesmo padrão;
- rejeições altas com pouca ou nenhuma aceitação;
- saldo de feedback ambíguo com histórico conflitante;
- score fraco combinado com rejeição recorrente.

Ao detectar instabilidade, o padrão é marcado com `is_unstable = 1` e sua influência futura é reduzida ou removida do contexto operacional.

### 5.5 Governança da Memória

**Arquivo:** `src/brain4me/memory_governance.py`

Funções implementadas:

```python
def list_patterns(db_path: str | Path, limit: int = 20) -> list[dict[str, object]]
def remove_pattern(db_path: str | Path, pattern_id: str) -> None
def update_pattern_score(db_path: str | Path, pattern_id: str, new_score: float) -> None
```

Estratégia:

- listagem usa score final dinâmico;
- remoção é lógica, via `valid_to`, sem destruição;
- ajuste manual altera `confidence_score` e `score` base.

### 5.6 Explicação Explícita do Aprendizado

**Arquivos:** `src/brain4me/decision_engine.py`, `src/brain4me/context_builder.py`

O sistema agora inclui mensagens do tipo:

```text
Baseado em aprendizado: esta decisão foi aceita X vezes, rejeitada Y vezes.
```

Além disso:

- o contexto inclui seção de decisões influenciadas por memória;
- apenas padrões fortes e estáveis seguem para contexto relevante;
- padrões instáveis deixam de contaminar a resposta.

---

## 6. Extensões Incrementais de Schema

### `memory_entries`

Foram adicionados campos leves:

- `confidence_score`
- `frequency`
- `last_used_at`
- `feedback_balance`
- `normalized_key`
- `is_unstable`

### `feedback_entries`

Foram adicionados:

- `decision_key`
- `correction_key`

Essas extensões sustentam normalização, estabilidade e agregação sem criar uma tabela paralela para aprendizado.

---

## 7. CLI e UI

### CLI

Novos comandos:

```bash
brain memory --db <db> list
brain memory --db <db> remove <pattern_id>
brain memory --db <db> review
```

Uso:

- listar padrões ativos com score e confiança;
- remover padrões manualmente;
- revisar buckets de padrões fortes, rejeitados e instáveis.

### UI

**Arquivo:** `app.py`

Novo painel lateral:

- `Aprendizado do sistema`
- padrões fortes
- padrões rejeitados
- padrões instáveis
- exclusão manual de padrão

O sistema continua oferecendo feedback operacional, mas agora a memória aprendida fica visível e governável.

---

## 8. Testes e Verificação

### Testes adicionados na fase

| Teste | Objetivo |
|---|---|
| `test_compute_memory_score_rewards_recent_frequent_confident_patterns` | valida score evolutivo |
| `test_apply_feedback_penalty_strongly_reduces_repeated_rejections` | valida penalização forte |
| `test_normalize_decision_text_groups_superficial_variants` | valida agrupamento superficial |
| `test_detect_unstable_pattern_flags_conflicting_feedback` | valida detecção de instabilidade |
| `test_governance_can_list_update_and_remove_patterns` | valida governança básica |
| `test_fetch_relevant_memories_discards_unstable_patterns` | valida filtro protetivo |
| `test_decision_engine_avoids_penalized_patterns_and_explains_learning` | valida impacto do aprendizado na sugestão |
| `test_cli_memory_commands_support_list_review_and_remove` | valida CLI de memória |

### Comandos executados

```bash
python -m pytest tests/test_phase5.py -q
python -m pytest -q
python -c "import streamlit, app; print('ok')"
```

### Resultado observado

- `tests/test_phase5.py`: `8 passed`
- suíte completa: `65 passed`
- import de `app.py`: `ok`

### Observação

O import do Streamlit fora de `streamlit run` continua gerando warnings esperados de `ScriptRunContext`, sem erro funcional.

---

## 9. Limitações Atuais

### Limitações funcionais

- a normalização ainda é heurística, não semântica profunda;
- a instabilidade é baseada em regras simples, não em inferência probabilística;
- correções diferentes são detectadas como conflito textual, não como conflito de intenção;
- o score evolutivo ainda usa janelas fixas e pesos estáticos.

### Limitações arquiteturais

- o aprendizado continua acoplado a `memory_entries`, o que é bom para simplicidade, mas limita especialização futura;
- o score final é recalculado sob demanda e não em job dedicado;
- a UI faz governança básica, mas não oferece workflow completo de revisão.

### Limitações de produto

- não há histórico visual da evolução de um padrão;
- não há comparação entre score anterior e score atual no painel;
- não existe ainda aprovação por lote ou revisão supervisionada de vários padrões.

---

## 10. Riscos Técnicos

- padrões semanticamente parecidos ainda podem divergir se a normalização não cobrir a variação;
- um excesso de regras locais pode endurecer demais o sistema e reduzir adaptação legítima;
- a governança manual ainda depende do operador entender score, rejeição e instabilidade;
- feedback inconsistente em baixo volume continua sendo um caso difícil de distinguir de mudança real de contexto.

---

## 11. Impacto da Fase 5

Antes:

```text
Sistema aprende
```

Depois:

```text
Sistema aprende → controla → melhora → evita erro
```

Na prática:

- o aprendizado deixou de ser cumulativo ingênuo;
- memória ruim pode ser isolada;
- padrões fortes ganham prioridade real;
- feedback conflitante deixa de contaminar a próxima recomendação com o mesmo peso.

---

## 12. Próximos Passos Recomendados

### Prioridade alta

1. adicionar visão histórica por padrão com evolução de score;
2. permitir ajuste manual de confiança diretamente na UI;
3. expor ao usuário final qual padrão foi descartado por instabilidade;
4. calibrar pesos do score evolutivo com exemplos reais de uso;
5. registrar motivos de remoção manual para auditoria.

### Prioridade média

1. criar limpeza automática de padrões fracos e antigos;
2. separar aprendizado por compartimento ou domínio;
3. gerar relatório periódico de padrões mais confiáveis e padrões problemáticos;
4. adicionar revisão assistida de feedback conflitante.

### Alinhamento com uma Fase 6

A base necessária para aprendizado supervisionado mais robusto já está pronta:

- score dinâmico;
- penalização explícita;
- bucketização de estabilidade;
- governança manual;
- explicação do aprendizado no pipeline de decisão.

---

## 13. Conclusão

A Fase 5 foi concluída com sucesso técnico dentro do recorte incremental definido. O Brain4me agora não apenas aprende com feedback, mas controla a qualidade desse aprendizado, reduz influência de padrões ruins, preserva explicabilidade e oferece mecanismos de governança para manter o sistema útil ao longo do tempo.
