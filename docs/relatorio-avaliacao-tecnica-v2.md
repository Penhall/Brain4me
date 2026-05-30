# Relatório de Avaliação Técnica — Brain4me MVP · Pós-Fase 2
**Data:** 2026-04-30
**Branch avaliado:** `main` (5b2525a)
**Avaliação:** revisão externa para ChatGPT

---

## 1. Resumo Executivo

A Fase 2 adicionou um módulo de montagem de contexto (`context_builder.py`), a dataclass `AnswerResult`, rastreabilidade de fontes via `SourceReference`, integração do LLM no fluxo de consulta e 6 novos testes. O sistema agora possui um pipeline completo: recuperação → montagem de contexto → chamada LLM → resposta. Em modo degradado (sem LLM), retorna texto estruturado legível.

Porém, há dois bugs críticos que comprometem a qualidade real da integração: **(1)** o `OpenAICompatibleResponseProvider` envia um system prompt de extração de Markdown ("retorne apenas JSON com entities e context") mesmo quando chamado no fluxo de consulta — o LLM receberá instruções contraditórias e provavelmente retornará JSON em vez de resposta em linguagem natural; **(2)** as fontes recuperadas do banco (`SourceReference`) nunca são passadas para `build_context_for_question`, então o prompt LLM sempre exibe "(nenhuma fonte registrada)" independente dos dados existentes. O sistema gera resposta em linguagem natural apenas se o LLM ignorar seu system prompt. A explicabilidade é estrutural (seções predefinidas no prompt), mas não foi testada com LLM real. O modo degradado é funcional e útil. A CLI `--json` retorna apenas os campos de `TopicExplanation`, não o `AnswerResult` completo conforme o spec original exigia.

---

## 2. Diferença em Relação à Fase 1

| Aspecto | Fase 1 | Fase 2 |
|---|---|---|
| `ask_question` retorna | `TopicExplanation` (struct) | `AnswerResult` (struct + answer text) |
| Resposta em NL | Não | Sim (se LLM configurado e bug contornado) |
| Fontes na resposta | Não | `SourceReference` (note_id, title, source_path, label) |
| Contexto montado | Não | `build_context_for_question` com limite de chars |
| Modo degradado | Não existia | Sim — retorna texto estruturado |
| Rastreabilidade | Nenhuma | Parcial (fontes listadas, mas desconectadas do prompt LLM) |
| Testes | 34 | 40 (+6 novos) |

**Ganho prático real:** o modo degradado já melhora a UX — a resposta de texto estruturado é mais legível que o struct bruto da Fase 1. A arquitetura do pipeline está correta. Os bugs são de ligação entre componentes, não de design.

---

## 3. Context Builder

**Existe módulo dedicado?** Sim — `src/brain4me/context_builder.py`.

**Funções principais:**
- `_build_sections(explanation)` — mapeia tipo de explicação para lista de seções ordenadas por prioridade
- `build_context_for_question(question, explanation, *, max_chars=12000) -> BuiltContext`
- `build_answer_prompt(question, context) -> str`

**Como o contexto é montado:**
Seções são montadas em ordem de prioridade fixa. Para `TopicExplanation`: Decisões → Evidências → Riscos → Alternativas. Para `EntityExplanation`: Decisões → Contexto → Histórico → Conflitos → Relações. Cada seção vira um bloco Markdown (`### Seção\n- item1\n- item2`). Seções são concatenadas com `\n\n`.

**Há priorização por score?** Indiretamente — as queries SQL que alimentam `TopicExplanation` e `EntityExplanation` já ordenam por `score DESC`. Dentro de cada seção os itens chegam por score decrescente. Mas a prioridade *entre seções* é fixa (decisões sempre antes de evidências), independente de scores relativos.

**Há limite de tamanho?** Sim — `max_chars=12000` por padrão. O truncamento é por seção inteira (corta texto bruto se não couber seção completa) com fallback que garante contexto nunca vazio.

**O que entra no contexto:**

| Tipo | Para TopicExplanation | Para EntityExplanation |
|---|---|---|
| Decisões | ✅ | ✅ |
| Evidências | ✅ | ❌ (usa "Contexto") |
| Riscos | ✅ | ❌ |
| Alternativas | ✅ | ❌ |
| Histórico | ❌ | ✅ |
| Conflitos | ❌ | ✅ |
| Relações | ❌ | ✅ |

**Avaliação:**
- O formato de seções em Markdown com `###` e listas é adequado para LLMs
- O limite de 12.000 chars é razoável para a maioria dos modelos
- **Problema grave:** `BuiltContext.sources` é sempre `[]` — as fontes do banco nunca chegam ao prompt
- Sem mecanismo de deduplicação de conteúdo idêntico entre seções
- Histórico de memória não entra no contexto de `TopicExplanation` — potencial perda de contexto temporal

---

## 4. Integração com LLM

**Onde o LLM é chamado:** `ask_question()` em `src/brain4me/query.py`.

**O LLM é opcional?** Sim — se `BRAIN4ME_LLM_API_KEY` e `BRAIN4ME_LLM_MODEL` não estiverem configurados, `build_openai_compatible_provider_from_env()` retorna `None` e o sistema opera em modo degradado.

**Há fallback se falhar?** Sim — qualquer `Exception` é capturada silenciosamente e retorna `degraded=True` com texto estruturado.

**Há timeout?** Sim — timeout de 30s hardcoded em `_default_http_post`. Sem retry.

**O prompt é estruturado?** Sim — `build_answer_prompt` produz prompt com seções definidas e instruções explícitas.

**Bug crítico — system prompt errado:**

O `OpenAICompatibleResponseProvider` foi projetado para extração (Fase 1) e reutilizado na consulta sem modificação. Quando `ask_question` chama `provider(prompt_de_resposta)`, o LLM recebe:

- **System:** `"Extraia conhecimento estruturado de Markdown e retorne apenas JSON com as chaves 'entities' e 'context'."`
- **User:** `"Você é um assistente de segundo cérebro... formate sua resposta em seções..."`

As instruções são contraditórias. A maioria dos LLMs dará prioridade ao system prompt e retornará JSON de extração, não a resposta formatada. **A integração LLM não funciona como projetado em produção.**

**Avaliação:**
- A arquitetura (provider injetável, fallback, modo degradado) é boa
- O bug do system prompt anula o valor da integração em produção
- Sem LLM real testado, o bug não foi detectado nos testes

---

## 5. Prompt Utilizado pelo LLM

**Como é construído:** `build_answer_prompt(question, context)` em `context_builder.py`.

**Estrutura real do que o LLM recebe:**
```
System (errado — vem do llm_client): "Extraia conhecimento estruturado de Markdown..."
User (correto — vem do prompt):
  - Instrução: responda em PT-BR, use só o contexto, não invente, cite fontes
  - Template de formato com 5 seções
  - Pergunta
  - Contexto (seções Markdown)
  - Fontes (sempre "(nenhuma fonte registrada)" por causa do bug)
```

**Seções esperadas na resposta:**
- `## Resposta direta`
- `## Justificativa`
- `## Riscos e conflitos`
- `## Próximos passos`
- `## Fontes`

**Instrução de não inventar:** Presente — "Use somente o contexto fornecido. Não invente informações."

**Instrução de citar fontes:** Presente, mas ineficaz — fontes estão sempre vazias no `context_block`.

**Avaliação:**
- O template do prompt é bem estruturado e adequado para QA sobre base de conhecimento
- As instruções anti-alucinação estão presentes
- O system prompt do cliente LLM sabota completamente o prompt do usuário
- `temperature=0` é adequado para respostas determinísticas e factuais
- Sem o bug, o prompt teria boa probabilidade de produzir respostas úteis

---

## 6. Uso do Context Graph

**O Context Graph é usado na consulta?** Indiretamente — `find_decision_rows` consulta `context_nodes` e `context_edges` via SQL para encontrar decisões associadas por contexto. `fetch_decision_context` também consulta essas tabelas.

**O NetworkX `build_context_graph` é usado na consulta?** Não. Os objetos NetworkX são construídos apenas em `summary_command` e `export_command`.

**Ele influencia a resposta?** Sim, indiretamente — decisões encontradas via Context Graph entram no `TopicExplanation.decisions` e depois no contexto LLM.

**É usado no ranking?** Não — o ranking é por `score DESC` no SQL, não por propriedades do grafo.

**Avaliação:**
- O risco de "virar tabela auxiliar" foi parcialmente concretizado: as relações semânticas do Context Graph estão disponíveis no banco mas não são exploradas como grafo na consulta
- Não há traversal de grafo, subgrafo de vizinhança, cálculo de centralidade ou path finding
- O Context Graph existe como estrutura relacional no banco, não como grafo ativo no raciocínio

---

## 7. Uso do Knowledge Graph

**O KG (NetworkX) é usado na query?** Não. `build_knowledge_graph` é chamado apenas em `summary_command` e `export_command`.

**Ele participa da resposta?** Não. As entidades e relações são consultadas via SQL direto em `fetch_entity_relations` e `fetch_related_decision_entities`.

**Ele influencia o contexto?** Não diretamente. As relações entre entidades chegam ao `EntityExplanation.relations` via SQL, não via traversal do grafo NetworkX.

**Avaliação:** O Knowledge Graph é um artefato de exportação/visualização, não um componente ativo do raciocínio. Toda a lógica de consulta usa SQL direto nas tabelas `entities` e `relations`. Isso é funcional mas perde as vantagens de usar grafos: traversal em profundidade, cálculo de relevância por vizinhança, detecção de ciclos.

---

## 8. Resposta ao Usuário (`brain ask`)

**O sistema retorna resposta em linguagem natural?**
- Com LLM funcional (após correção do bug): sim
- Em modo degradado: não — retorna texto estruturado legível mas sem síntese

**Separação em seções (quando LLM funciona):**
- ✅ Resposta direta
- ✅ Justificativa
- ✅ Riscos e conflitos
- ✅ Próximos passos
- ✅ Fontes

**Indicação de modo degradado:** Sim — `[Modo degradado: LLM não disponível ou falhou]` impresso após a resposta.

**Avaliação:**

| Aspecto | Situação |
|---|---|
| Qualidade com LLM real | Não testável em produção (bug de system prompt) |
| Modo degradado | Funcional e claro |
| Indicação de degradação | Clara e explícita |
| Usabilidade | Parcial — modo degradado funciona, modo LLM não |

---

## 9. Fontes e Rastreabilidade

**A resposta cita fontes?**
- `AnswerResult.sources` — sim, lista de `SourceReference` com `note_id`, `source_path`, `title`, `label`
- Na CLI texto — sim, exibidos após a resposta
- No prompt LLM — não (`built_context.sources` é sempre `[]`)

**O bug de desconexão:**

```python
# ask_question em query.py
sources = fetch_sources_for_decisions(conn, decision_ids)   # ← fontes corretas do banco

built_context = build_context_for_question(question, explanation)  # ← sources NÃO passadas
# built_context.sources == []  sempre

provider(build_answer_prompt(question, built_context))  # ← LLM não vê as fontes
```

As fontes chegam ao `AnswerResult.sources` e são exibidas na CLI. O LLM, porém, não as vê e não pode citá-las nas seções `## Fontes` da resposta sintetizada.

**Avaliação:**
- A estrutura de rastreabilidade está correta (`SourceReference` bem definido, query com GROUP BY)
- A exibição na CLI é útil e auditável
- A desconexão fontes↔prompt torna a citação automática não-funcional
- A auditoria é possível manualmente via `source_path` e `note_id` exibidos

---

## 10. Modo Degradado

**O que acontece quando o LLM falha?** `_format_structured_answer` formata a `TopicExplanation` ou `EntityExplanation` como texto plano com seções (Decisões encontradas, Evidências, Riscos, Alternativas).

**O sistema continua funcional?** Sim — este é o comportamento padrão atual já que nenhum LLM está configurado nos testes.

**O retorno estruturado ainda é útil?** Sim. Exemplo de saída:

```
Pergunta: SQLite

Decisões encontradas:
- usar SQLite no MVP

Evidências:
- reduz complexidade operacional

Riscos:
- consultas relacionais avancadas podem exigir revisao futura

Alternativas:
- Neo4j
```

É mais legível que o JSON bruto da Fase 1, mas não tem síntese nem justificativa contextualizada.

---

## 11. Testes da Fase 2

| Teste | O que cobre | Tipo |
|---|---|---|
| `test_context_builder_produces_nonempty_context_from_explanation` | context_builder com dados reais, score > 0, degraded=False | Unitário |
| `test_context_builder_respects_max_chars_limit` | truncamento por max_chars | Unitário |
| `test_ask_question_uses_llm_when_provider_available` | provider mockado retorna resposta, degraded=False | Integração (mock) |
| `test_ask_question_degrades_gracefully_when_llm_fails` | provider falha → degraded=True, answer não-vazio | Integração (mock) |
| `test_cli_ask_json_output_has_expected_fields` | `--json` retorna topic e decisions | CLI |
| `test_ask_question_returns_sources_when_notes_exist` | sources é lista, cada item tem campos corretos | Integração (DB) |

**Avaliação:**
- ✅ Context builder coberto (montagem e truncamento)
- ✅ LLM mockado coberto (sucesso e falha)
- ✅ Fallback degradado coberto
- ⚠️ CLI JSON testado apenas por presença de `topic` e `decisions` — não verifica `answer`, `degraded`, `sources` no JSON (porque `--json` retorna `structured`, não `AnswerResult`)
- ❌ Nenhum teste verifica que fontes chegam ao prompt LLM (o bug não é detectado)
- ❌ Nenhum teste verifica a estrutura das seções do prompt (`build_answer_prompt`)
- ❌ Nenhum teste verifica compatibilidade entre system prompt do `llm_client` e o prompt de resposta

---

## 12. Mudanças na CLI

| Aspecto | Antes (Fase 1) | Depois (Fase 2) |
|---|---|---|
| Saída texto | Lista estruturada (Topic, Decisions, Evidence...) | `result.answer` (NL ou estruturado) |
| Indicador de degradação | Não existia | Sim — `[Modo degradado: ...]` |
| Fontes exibidas | Não | Sim — lista com title e label |
| `--json` retorna | `asdict(TopicExplanation)` | `asdict(result.structured)` = `asdict(TopicExplanation)` |

**O JSON mudou?** Não na prática — `--json` ainda serializa `result.structured` (a `TopicExplanation`), que tem os mesmos campos de antes. O spec original exigia `{question, answer, degraded, sources, structured}` mas a implementação retorna apenas os campos de `TopicExplanation`. Este é um gap de implementação.

**O usuário percebe a diferença?** Sim — a saída texto é claramente melhor (mais concisa, com indicador de modo e fontes). A diferença no JSON não é perceptível para quem esperava o spec completo.

---

## 13. Performance

| Componente | Custo estimado | Observação |
|---|---|---|
| `build_context_for_question` | O(n) em items | Negligível |
| `fetch_sources_for_decisions` | SQL com GROUP BY em colunas indexadas | Aceitável para MVP |
| `explain_topic` | 1 query com 4 OR conditions + 3 queries adicionais | Cresce com o corpus |
| `build_knowledge_graph` / `build_context_graph` | SELECT * em todas as tabelas, reconstrução completa | Chamado em summary e export, não em ask |
| Chamada LLM | 30s timeout, sem retry, síncrona | Gargalo principal em produção |
| Double query em `ask_question` | `find_decision_rows` chamado 2x (em `explain_topic` e depois para buscar fontes) | Redundância desnecessária |

**Gargalo principal:** a chamada LLM é síncrona e bloqueante. Sem retry, uma falha de rede descarta a resposta em silêncio.

**Redundância identificada:** em `ask_question`, `find_decision_rows` é chamado duas vezes — uma dentro de `explain_topic` e outra para buscar fontes. A segunda chamada poderia ser eliminada reutilizando os `decision_ids` já obtidos.

---

## 14. Riscos Arquiteturais

**Context Graph virando tabela auxiliar:** Risco materializou-se parcialmente. O NetworkX só é construído para exportação. Consultas usam SQL direto. Não há traversal real de grafo.

**Contexto mal montado (ruído):** Risco moderado. Itens de baixo score chegam ao contexto caso a seção não seja truncada. Sem deduplicação semântica, decisões similares podem aparecer como itens distintos.

**Dependência excessiva do LLM:** Mitigado pelo modo degradado. Mas o bug do system prompt significa que a dependência atual *não entrega valor*.

**Perda de rastreabilidade:** A fonte não chega ao prompt do LLM. O LLM gera resposta sem ancoragem real nas fontes recuperadas. Se o LLM inventar algo, o usuário vê fontes listadas abaixo, mas a resposta pode não ter sido gerada a partir delas.

**Crescimento do contexto sem controle:** O limite de `max_chars=12000` é uma barreira, mas o truncamento é abrupto (corta texto no meio de uma seção). Sem paginação inteligente ou seleção por relevância.

**Duplicação de informação:** `_format_structured_answer` e `build_context_for_question` cobrem o mesmo território com lógicas separadas. Se o schema mudar, ambas precisam ser atualizadas.

**Sem transação no ingest:** Crítico da Fase 1, não resolvido na Fase 2.

---

## 15. Lacunas

### Crítico

- **Bug: system prompt do `llm_client` é de extração**, não de resposta — o `OpenAICompatibleResponseProvider` instrui o LLM a "retornar apenas JSON com entities e context" mesmo no fluxo de consulta; a integração LLM não funciona como projetado
- **Bug: fontes não chegam ao prompt LLM** — `built_context.sources` é sempre `[]`; a variável `sources` retornada por `fetch_sources_for_decisions` nunca é passada para `build_context_for_question`
- **CLI `--json` não retorna `AnswerResult`** — retorna apenas `asdict(TopicExplanation)`; o spec exigia `{question, answer, degraded, sources, structured}`
- **Sem transação explícita no pipeline de ingestão** — herdado da Fase 1, não corrigido

### Importante

- `find_decision_rows` chamado duas vezes em `ask_question` — redundância de query
- Modo degradado não usa separação em seções (`## Resposta direta` etc.) — experiência inconsistente com modo LLM
- `brain review decisions`, `brain memory`, `brain curate` ainda ausentes
- `recency` e `frequency` do scoring fixos em `1.0` — score não reflete tempo real
- Grafos NetworkX reconstruídos do zero a cada chamada — sem cache
- `build_answer_prompt` sem versão ou identificador — difícil rastrear qual prompt gerou qual resposta

### Futuro

- Traversal real do Context Graph para contextualização mais profunda
- Embeddings para busca semântica densa (alternativa ao LIKE)
- Cache de grafos invalidado na ingestão
- `brain memory episodes` e `brain memory patterns`
- Streaming da resposta LLM
- Retry com backoff exponencial no cliente LLM
- Expiração de `memory_entries` (valid_to)

---

## 16. Avaliação Final

| Dimensão | Nota | Justificativa |
|---|---|---|
| **Arquitetura** | 7/10 | Pipeline bem estruturado, separação de responsabilidades clara, AnswerResult/BuiltContext bem modelados. Penalizado pelo bug de ligação fontes↔prompt e pelo system prompt errado. |
| **Implementação** | 5/10 | Código limpo e tipado, testes passam, mas dois bugs críticos de ligação entre componentes que só seriam detectados com LLM real. |
| **Inteligência do sistema** | 4/10 | O raciocínio ainda é retrieval estruturado + formatação. O LLM não está funcionalmente integrado. O Context Graph não é traversado. |
| **Explicabilidade** | 6/10 | Modo degradado é legível. Fontes são listadas na CLI. Mas o LLM não ancora as respostas nas fontes. O Context Graph de conflitos não é surfaceado para o usuário. |
| **Pronto para uso real** | 3/10 | Modo degradado é usável. Modo LLM tem bugs críticos. Sem transação no ingest. CLI JSON incompleto. Nenhum LLM real foi testado. |

---

## 17. Próximos Passos Recomendados

Em ordem de impacto:

1. **Corrigir o system prompt do `llm_client`** — criar `build_qa_provider_from_env()` separado do de extração, com system prompt neutro ou orientado a QA. Este único fix desbloqueia toda a integração LLM.

2. **Passar fontes para `build_context_for_question`** — adicionar parâmetro `sources: list[SourceReference]` à função e preencher `BuiltContext.sources`. Fix de 3 linhas em `ask_question`.

3. **Corrigir CLI `--json`** — retornar `{question, answer, degraded, sources: [...], structured: {...}}` em vez de apenas `asdict(result.structured)`.

4. **Envolver ingestão em transação explícita** — `BEGIN IMMEDIATE / COMMIT / ROLLBACK` em `ingest_markdown_note`. Crítico para consistência.

5. **Eliminar a segunda chamada a `find_decision_rows`** em `ask_question` — reaproveitar os `decision_ids` já obtidos do primeiro `explain_topic`.

6. **Adicionar seções ao modo degradado** — fazer `_format_structured_answer` usar os mesmos cabeçalhos `## Resposta direta`, `## Justificativa` etc. para consistência de UX.

7. **Teste de integração com LLM real (ou mock com resposta estruturada)** — verificar que a resposta LLM tem as 5 seções esperadas quando o prompt correto é enviado.

8. **Implementar `brain review decisions`** — listar decisões com filtro e score mínimo.

9. **Implementar `brain memory episodes`** — consultar `memory_entries` com filtros por tipo e período.

10. **Adicionar índices SQL** — em `entities(canonical_name)` e `context_nodes(content)` para escalar queries LIKE.

---

*Relatório gerado por análise estática do repositório em `main` (5b2525a). Nenhum arquivo do projeto foi alterado.*
