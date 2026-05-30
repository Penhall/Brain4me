# Relatório Técnico — Brain4me · Fase 3
**Data:** 2026-04-30
**Branch avaliado:** `main`
**Commit base:** `310227c`

---

## 1. Resumo Executivo

A Fase 3 transformou o fluxo de consulta do Brain4me de um retrieval estruturado para um pipeline de raciocínio orientado por intenção, grafo e memória. O sistema agora classifica a intenção da pergunta, recupera entidades candidatas, expande contexto usando Knowledge Graph e Context Graph, incorpora memórias relevantes, sugere decisões quando aplicável e responde mantendo compatibilidade com CLI e modo degradado.

Também foi adicionada uma interface web simples com Streamlit para uso real. A implementação foi feita sem alterar o schema do banco, sem remover funcionalidades existentes e sem quebrar a suíte de testes atual.

**Status de verificação:** `51 testes passando`.

---

## 2. Escopo Entregue

### Implementado nesta fase

- classificação de intenção via heurística em `intent.py`;
- expansão real de contexto por grafos em `query.py`;
- uso efetivo de nós do Context Graph no contexto montado;
- recuperação de memória ativa em `memory.py`;
- sugestão de decisão em `decision_engine.py`;
- enriquecimento do `AnswerResult` com metadados de raciocínio;
- atualização da CLI para expor os novos campos;
- interface web em `app.py` com Streamlit;
- testes dedicados para os novos comportamentos.

### Mantido sem ruptura

- schema SQLite existente;
- pipeline de ingestão;
- CLI anterior;
- modo degradado sem LLM;
- explainers existentes (`explain_topic`, `explain_entity`);
- fallback adaptativo do extrator.

---

## 3. Fluxo Atual de Consulta

O fluxo de `ask_question` passou a operar assim:

```text
question
→ classify_intent
→ retrieve entities
→ expand_graph_context
→ fetch_relevant_memories
→ build_context
→ suggest_decision (quando intent = decision_support)
→ LLM ou fallback estruturado
→ AnswerResult enriquecido
```

### Intents suportadas

- `fact_lookup`
- `decision_support`
- `risk_analysis`
- `explanation`
- `exploration`

---

## 4. Arquivos Criados e Alterados

### Novos arquivos

| Arquivo | Responsabilidade |
|---|---|
| `src/brain4me/intent.py` | classificação heurística de intenção |
| `src/brain4me/memory.py` | recuperação de memórias relevantes |
| `src/brain4me/decision_engine.py` | sugestão de decisão com fallback heurístico e uso opcional de LLM |
| `app.py` | interface web Streamlit |
| `docs/superpowers/plans/2026-04-30-fase-3-raciocinio.md` | plano de implementação da fase |

### Arquivos alterados

| Arquivo | Mudança principal |
|---|---|
| `src/brain4me/query.py` | novo pipeline de raciocínio, expansão de grafo e integração de memória |
| `src/brain4me/context_builder.py` | contexto enriquecido com intenção, memórias, inferências, conflitos e decisão sugerida |
| `src/brain4me/models.py` | adição de `GraphContext` e novos campos em `AnswerResult` |
| `src/brain4me/graphs.py` | grafos com metadados adicionais em nós e arestas |
| `src/brain4me/query_helpers.py` | helpers de busca de entidades e links para contexto |
| `src/brain4me/cli.py` | payload JSON ampliado e exibição de decisão sugerida |
| `src/brain4me/extractor.py` | ajuste de prioridade para preservar notas estruturadas sem quebrar fallback |
| `tests/conftest.py` | fixtures da Fase 3 |
| `tests/test_phase3.py` | cobertura da fase |
| `pyproject.toml` | dependência `streamlit` |

---

## 5. Componentes Técnicos

### 5.1 Intent Classifier

**Arquivo:** `src/brain4me/intent.py`

Implementado com regras heurísticas simples baseadas em keywords e prioridade entre intents. Não depende exclusivamente de LLM.

**Decisão técnica:** usar heurística local primeiro para manter previsibilidade, baixo acoplamento e funcionamento offline.

### 5.2 Graph-Based Retrieval

**Arquivo:** `src/brain4me/query.py`

Foi criada a função:

```python
def expand_graph_context(db_path: str | Path, entity_ids: list[str], depth: int = 2) -> GraphContext:
```

Ela:

- resolve seeds para múltiplas entidades compatíveis;
- percorre vizinhos do Knowledge Graph e do Context Graph;
- limita profundidade;
- evita loops com conjunto de visitados;
- coleta entidades conectadas, decisões, evidências, alternativas, riscos, conflitos e inferências.

### 5.3 Context Builder Enriquecido

**Arquivo:** `src/brain4me/context_builder.py`

O `BuiltContext` agora transporta:

- `intent`
- `decisions`
- `evidence`
- `alternatives`
- `risks`
- `conflicts`
- `memories`
- `inferences`
- `detected_entities`
- `suggested_decision`

O texto de contexto prioriza:

- decisão sugerida;
- decisões e evidências;
- conflitos;
- inferências;
- memórias relevantes;
- entidades conectadas.

### 5.4 Decision Engine

**Arquivo:** `src/brain4me/decision_engine.py`

Função implementada:

```python
def suggest_decision(context: BuiltContext) -> str:
```

Comportamento:

- usa LLM quando disponível;
- cai para fallback heurístico quando não há provider ou quando a chamada falha;
- gera recomendação, alternativas, riscos e base usada.

### 5.5 Memória Ativa

**Arquivo:** `src/brain4me/memory.py`

Função implementada:

```python
def fetch_relevant_memories(db_path: str | Path, question: str, entity_ids: list[str] | None = None, *, limit: int = 5) -> list[str]:
```

Recupera memórias por:

- entidade relacionada;
- conteúdo textual da memória;
- `canonical_name` da entidade associada.

### 5.6 Interface Web

**Arquivo:** `app.py`

A UI implementada oferece:

- campo de pergunta;
- botão `Consultar`;
- exibição de resposta;
- painel de justificativa;
- painel de riscos;
- fontes;
- sidebar com histórico, entidades detectadas, decisão sugerida e memórias.

---

## 6. Contrato Atual do Resultado

O `AnswerResult` passou a incluir, além do comportamento anterior:

- `intent`
- `justification`
- `risks`
- `detected_entities`
- `suggested_decision`
- `memories`

Isso permite:

- manter o output atual da CLI;
- expor estado de raciocínio para UI;
- sustentar testes de integração mais ricos.

---

## 7. Testes e Verificação

### Testes adicionados na fase

| Teste | Objetivo |
|---|---|
| `test_classify_intent_distinguishes_decision_risk_and_exploration` | valida classificação de intent |
| `test_expand_graph_context_collects_entities_conflicts_and_inferences` | valida travessia e coleta por grafo |
| `test_fetch_relevant_memories_returns_decision_history_for_question` | valida memória ativa |
| `test_suggest_decision_uses_context_without_llm` | valida fallback do decision engine |
| `test_ask_question_returns_reasoning_metadata_and_suggested_decision` | valida integração fim a fim da Fase 3 |

### Comandos executados

```bash
python -m pytest tests/test_phase3.py -q
python -m pytest -q
python -c "import streamlit, app; print('ok')"
```

### Resultado observado

- `tests/test_phase3.py`: `11 passed`
- suíte completa: `51 passed`
- import de `app.py`: `ok`

### Observação

O import do Streamlit fora de `streamlit run` gera warnings esperados de `ScriptRunContext`, mas não indica erro funcional da aplicação.

---

## 8. Limitações Atuais

### Limitações funcionais

- o intent classifier ainda é heurístico e não usa fallback real para LLM;
- o decision engine usa prompt simples e não retorna estrutura tipada;
- memória ativa ainda usa busca textual e IDs relacionados, sem ranking semântico;
- o contexto expandido é reconstruído a cada consulta, sem cache;
- a UI é útil para validação manual, mas ainda não tem histórico persistente nem seleção explícita de banco por workspace de uso.

### Limitações arquiteturais

- `GraphContext` ainda é um agregado em memória, não um artefato persistido;
- a expansão por grafo opera sobre NetworkX reconstruído do banco a cada chamada;
- não há score específico para inferência de resposta final além dos scores já persistidos em entidades/contexto.

### Limitações de produto

- não há auditoria visual do subgrafo usado em cada resposta;
- não há feedback loop para transformar respostas ou decisões aprovadas em nova memória procedural;
- a UI não inclui autenticação, upload de notas ou workflow de ingestão.

---

## 9. Riscos Técnicos

- aumento do custo de consulta à medida que o corpus cresce, já que a expansão por grafo reconstrói os grafos em cada chamada;
- maior variação de output quando o LLM estiver ativo, principalmente na sugestão de decisão;
- heurísticas de intenção e busca de memória podem enviesar respostas curtas ou ambíguas;
- a resposta final ainda depende de recuperação lexical inicial para achar seeds relevantes.

---

## 10. Impacto da Fase 3

Antes:

```text
Pergunta → contexto → resposta
```

Depois:

```text
Pergunta → intenção → entidades → grafo → memória → contexto → decisão → resposta
```

Na prática, isso muda o Brain4me de um consultor de fatos estruturados para um agente de consulta com sinais reais de raciocínio operacional.

---

## 11. Próximos Passos Recomendados

### Prioridade alta

1. persistir histórico de consultas e respostas na UI;
2. adicionar fallback opcional de LLM para desambiguação de intent;
3. melhorar ranking de memórias por recência, prioridade e tipo;
4. expor no resultado quais nós e relações do grafo sustentaram a resposta;
5. adicionar testes de regressão para perguntas ambíguas e múltiplas decisões concorrentes.

### Prioridade média

1. criar visualização do subgrafo usado em cada consulta;
2. separar melhor decisão recomendada de resposta final em estrutura tipada;
3. adicionar cache local de grafos por snapshot do banco;
4. incluir logs de reasoning path para auditoria.

### Alinhamento com Fase 4

A base necessária para memória evolutiva e autoaprendizado já está preparada:

- intenção explícita;
- memória ativa no fluxo;
- ponto dedicado para decisão;
- UI de uso real;
- resultado enriquecido com estado interno.

---

## 12. Conclusão

A Fase 3 foi concluída com sucesso técnico dentro das restrições definidas. O sistema passou a raciocinar sobre intenção, contexto conectado e memória sem ruptura de arquitetura nem de schema, e a base atual já sustenta uma próxima etapa focada em memória evolutiva, aprendizado incremental e otimização de retrieval.
