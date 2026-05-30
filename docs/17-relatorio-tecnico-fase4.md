# Relatório Técnico — Brain4me · Fase 4
**Data:** 2026-05-01
**Branch avaliado:** `main`
**Commit base:** `310227c`

---

## 1. Resumo Executivo

A Fase 4 transformou o Brain4me de um sistema que responde com contexto e decisão sugerida para um sistema que também aprende com uso real. O fluxo agora persiste rastros de raciocínio, recebe feedback explícito do usuário, converte esse feedback em memória evolutiva e reutiliza padrões aceitos ou rejeitados para influenciar contexto e recomendação futura.

A implementação foi incremental sobre a Fase 3. O schema existente foi preservado, com apenas duas extensões mínimas para persistência operacional: `reasoning_traces` e `feedback_entries`. O restante do aprendizado foi reaproveitado sobre `memory_entries`, preservando a arquitetura atual e a explicabilidade do sistema.

**Status de verificação:** `57 testes passando`.

---

## 2. Escopo Entregue

### Implementado nesta fase

- persistência de reasoning trace após cada `ask_question`;
- registro de feedback aceito, rejeitado e corrigido;
- armazenamento de padrões aprendidos em `memory_entries`;
- influência explícita da memória evolutiva no contexto e na decisão sugerida;
- ajuste do decision engine com base em decisões aceitas e rejeitadas;
- atualização da UI com botões de feedback e histórico aprendido;
- testes dedicados para reasoning, feedback e memória evolutiva.

### Mantido sem ruptura

- fluxo principal de ingestão;
- schema base do MVP;
- explainers e fluxo de consulta da Fase 3;
- modo degradado sem LLM;
- compatibilidade da CLI;
- contrato geral de resposta em linguagem natural.

---

## 3. Fluxo Atual de Consulta e Aprendizado

O fluxo de `ask_question` passou a operar assim:

```text
question
→ classify_intent
→ retrieve entities
→ expand_graph_context
→ fetch_relevant_memories
→ build_context
→ suggest_decision
→ resposta final
→ save_reasoning_trace
```

Após a resposta, a UI ou qualquer integração pode registrar:

```text
feedback do usuário
→ record_feedback
→ store_learned_pattern
→ memory_entries
→ influência em consultas futuras
```

Isso adiciona um segundo ciclo ao sistema:

```text
responde → registra → recebe feedback → aprende → melhora
```

---

## 4. Arquivos Criados e Alterados

### Novos arquivos

| Arquivo | Responsabilidade |
|---|---|
| `src/brain4me/reasoning_log.py` | persistência e leitura de rastros de raciocínio |
| `src/brain4me/feedback.py` | registro de feedback humano e vínculo com traces |
| `tests/test_phase4.py` | cobertura da Fase 4 |
| `docs/superpowers/plans/2026-05-01-fase-4-memoria-evolutiva.md` | plano de implementação da fase |

### Arquivos alterados

| Arquivo | Mudança principal |
|---|---|
| `src/brain4me/storage_schema.py` | adição das tabelas `reasoning_traces` e `feedback_entries` |
| `src/brain4me/models.py` | enriquecimento de `AnswerResult` com `context_text`, `db_path` e `trace_id` |
| `src/brain4me/memory.py` | suporte a `decision_pattern`, persistência e leitura de padrões aprendidos |
| `src/brain4me/context_builder.py` | priorização de decisões influenciadas por memória |
| `src/brain4me/decision_engine.py` | ajuste de sugestão com base em memórias aceitas e rejeitadas |
| `src/brain4me/query.py` | persistência automática de trace ao final de cada resposta |
| `app.py` | feedback funcional, histórico de decisões, padrões aprendidos e feedback recente |

---

## 5. Componentes Técnicos

### 5.1 Persistência de Raciocínio

**Arquivo:** `src/brain4me/reasoning_log.py`

Função implementada:

```python
def save_reasoning_trace(result: AnswerResult) -> None:
```

Ela persiste:

- pergunta;
- intent;
- entidades detectadas;
- contexto usado;
- decisão sugerida;
- resposta final;
- fontes;
- timestamp.

**Características de projeto:**

- tolera falha silenciosamente;
- não bloqueia o fluxo principal com exceção propagada;
- grava o `trace_id` de volta no próprio `AnswerResult` quando consegue persistir.

Também foi implementada:

```python
def fetch_recent_reasoning_traces(db_path: str | Path, limit: int = 10) -> list[dict[str, Any]]:
```

para alimentar UI e testes.

### 5.2 Feedback do Usuário

**Arquivo:** `src/brain4me/feedback.py`

Função implementada:

```python
def record_feedback(question: str, accepted: bool, correction: str | None = None, *, db_path: str | Path | None = None) -> None:
```

Tipos suportados:

- `accepted`
- `rejected`
- `corrected`

O feedback é associado ao trace mais recente da mesma pergunta e persiste:

- pergunta;
- resposta;
- decisão sugerida;
- tipo de feedback;
- correção;
- timestamp.

Também foi adicionada leitura operacional:

```python
def fetch_recent_feedback_entries(db_path: str | Path, limit: int = 10) -> list[dict[str, str]]:
```

### 5.3 Memória Evolutiva

**Arquivo:** `src/brain4me/memory.py`

Função implementada:

```python
def store_learned_pattern(db_path: str | Path, question: str, decision: str, accepted: bool) -> None:
```

Comportamento:

- decisão aceita → cria padrão com `Padrao aceito...`;
- decisão rejeitada → cria padrão com `Padrao rejeitado...`;
- correção → entra como novo padrão aceito.

A estratégia reutiliza `memory_entries` com:

- `memory_type = 'decision_pattern'`;
- prioridade dinâmica;
- score diferenciado para aceitação e rejeição.

Também foi adicionada:

```python
def fetch_learned_patterns(db_path: str | Path, limit: int = 10) -> list[str]:
```

### 5.4 Influência da Memória no Contexto

**Arquivo:** `src/brain4me/context_builder.py`

O `build_context_for_question` agora:

- reordena decisões quando há padrões aceitos ou rejeitados;
- inclui explicitamente blocos como `Decisões influenciadas por memória`;
- mantém `Memória relevante` visível no contexto final;
- preserva o restante do contexto da Fase 3.

Isso garante explicabilidade: o efeito da memória não fica implícito, ele aparece no contexto textual que alimenta o restante do pipeline.

### 5.5 Ajuste do Decision Engine

**Arquivo:** `src/brain4me/decision_engine.py`

O fallback do decision engine agora:

- calcula score local por memória associada à decisão;
- promove padrões aceitos;
- penaliza padrões rejeitados;
- inclui base textual do tipo `Baseado em decisoes anteriores...`.

O prompt LLM também passou a mencionar explicitamente memória histórica quando o provider estiver ativo.

### 5.6 UI com Feedback

**Arquivo:** `app.py`

A interface web passou a oferecer:

- botão `Consultar`;
- botão `Aceitar`;
- botão `Rejeitar`;
- campo de correção com `Salvar correcao`;
- sidebar com:
  - histórico de perguntas;
  - histórico de decisões;
  - padrões aprendidos;
  - feedback recente.

---

## 6. Extensões de Schema

Foram adicionadas duas tabelas novas em `storage_schema.py`.

### `reasoning_traces`

Guarda:

- `question`
- `intent`
- `detected_entities`
- `context_text`
- `suggested_decision`
- `answer`
- `sources_json`
- `created_at`

### `feedback_entries`

Guarda:

- `trace_id`
- `question`
- `answer`
- `suggested_decision`
- `feedback_type`
- `correction`
- `created_at`

### Observação arquitetural

O aprendizado em si não ganhou uma tabela nova. Ele foi deliberadamente mantido em `memory_entries`, usando `decision_pattern`, para reduzir acoplamento e evitar reescrita do sistema de memória atual.

---

## 7. Contrato Atual do Resultado

`AnswerResult` passou a incluir:

- `context_text`
- `db_path`
- `trace_id`

Esses campos não alteram a resposta final para o usuário, mas habilitam:

- persistência automática do trace;
- correlação de feedback com a execução anterior;
- inspeção e testes mais ricos;
- integração direta com a UI.

---

## 8. Testes e Verificação

### Testes adicionados na fase

| Teste | Objetivo |
|---|---|
| `test_ask_question_persists_reasoning_trace` | valida persistência do reasoning trace |
| `test_record_feedback_stores_feedback_with_latest_trace_context` | valida feedback aceito com contexto do trace |
| `test_record_feedback_with_correction_stores_learned_patterns` | valida rejeição com correção e memória aprendida |
| `test_store_learned_pattern_persists_decision_pattern_memory` | valida escrita de padrão aprendido em `memory_entries` |
| `test_decision_engine_adjusts_suggestion_based_on_feedback_memories` | valida influência da memória no decision engine |
| `test_ask_question_uses_learned_pattern_in_memories_and_answer` | valida reaproveitamento da memória em consulta futura |

### Comandos executados

```bash
python -m pytest tests/test_phase4.py -q
python -m pytest -q
python -c "import streamlit, app; print('ok')"
```

### Resultado observado

- `tests/test_phase4.py`: `6 passed`
- suíte completa: `57 passed`
- import de `app.py`: `ok`

### Observação

O import do Streamlit fora de `streamlit run` continua emitindo warnings esperados de `ScriptRunContext`, sem indicar erro funcional da aplicação.

---

## 9. Limitações Atuais

### Limitações funcionais

- o aprendizado ainda é baseado em matching textual, não semântico;
- feedback é registrado por pergunta, não por versão formal de resposta;
- o sistema ainda não diferencia claramente memória de aceitação por domínio, compartimento ou contexto temporal;
- correções humanas entram como novo padrão aceito, mas não reescrevem explicitamente uma decisão antiga.

### Limitações arquiteturais

- `reasoning_traces` e `feedback_entries` ainda não possuem camada própria de serviço além dos módulos atuais;
- o ranking de padrões é simples e usa regras locais, não um modelo de confiança acumulada;
- traces e feedback ainda não alimentam uma camada procedural separada da memória episódica.

### Limitações de produto

- não há visualização da linha do tempo de aprendizado;
- a UI não mostra diffs entre resposta original e correção;
- não há mecanismo de revisão, aprovação ou limpeza de padrões aprendidos.

---

## 10. Riscos Técnicos

- padrões aprendidos errados podem contaminar recomendações futuras se o usuário registrar feedback inconsistente;
- o reuso de memória textual pode favorecer decisões com nomes repetidos em contextos diferentes;
- o número de entradas em `reasoning_traces` e `feedback_entries` tende a crescer continuamente sem política de retenção;
- a influência da memória ainda é explicável, mas não calibrada quantitativamente em profundidade.

---

## 11. Impacto da Fase 4

Antes:

```text
Sistema responde
```

Depois:

```text
Sistema responde → registra → recebe feedback → aprende → influencia a próxima resposta
```

Na prática, isso transforma o Brain4me de um agente que raciocina em tempo de consulta para um agente que também acumula experiência operacional.

---

## 12. Próximos Passos Recomendados

### Prioridade alta

1. adicionar política de retenção ou compactação de `reasoning_traces`;
2. separar padrões aceitos, rejeitados e corrigidos com metadados mais estruturados;
3. melhorar o matching entre perguntas semelhantes para além de tokens literais;
4. expor no output da resposta qual memória pesou mais na recomendação;
5. adicionar testes de concorrência e tolerância a falha para persistência de feedback.

### Prioridade média

1. criar uma visualização de evolução por decisão ao longo do tempo;
2. permitir revisão e remoção de padrões aprendidos na UI;
3. incorporar compartimento e janela temporal no ranking de aprendizado;
4. gerar um resumo de “o que o sistema aprendeu recentemente”.

### Alinhamento com uma Fase 5

A base necessária para uma próxima etapa de autoaprendizado mais sofisticado já existe:

- reasoning trace persistido;
- feedback humano persistido;
- memória evolutiva reaproveitável;
- UI com ciclo de correção;
- reutilização explícita do aprendizado em consultas futuras.

---

## 13. Conclusão

A Fase 4 foi concluída com sucesso técnico dentro do recorte incremental definido. O Brain4me agora não apenas responde e sugere decisões, mas também registra como raciocinou, recebe correções humanas e reaproveita esse histórico para modular respostas futuras, mantendo a explicabilidade do fluxo e sem romper a arquitetura construída até aqui.
