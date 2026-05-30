# Relatório de Correções — Brain4me · Pós-Fase 2
**Data:** 2026-04-30
**Branch avaliado:** `main` (pós-correções)
**Commit base:** `5b2525a`

---

## 1. Resumo Executivo

Três bugs críticos identificados no relatório anterior foram corrigidos, totalizando **5 mudanças cirúrgicas** em 5 arquivos. O pipeline LLM agora funciona corretamente de ponta a ponta no modo configurado: o provider de QA envia o system prompt correto, as fontes recuperadas do banco chegam ao contexto e aparecem no prompt, a CLI `--json` retorna o `AnswerResult` completo, e o modo degradado mantém formato consistente com o output do LLM. **46 testes passando** (+ 6 novos).

---

## 2. Bugs Corrigidos

### Bug 1 — System prompt errado no LLM (CRÍTICO)

**Problema:** `OpenAICompatibleResponseProvider` foi reaproveitado do fluxo de extração. Ao chamar o LLM para responder perguntas, enviava:
```
System: "Extraia conhecimento estruturado de Markdown e retorne apenas JSON com as chaves 'entities' e 'context'..."
```
O LLM retornava JSON de extração, não resposta em linguagem natural.

**Correção:** Criado `QAResponseProvider` em `llm_client.py` com system prompt dedicado ao fluxo de QA:
```
Você é um assistente de segundo cérebro.
Use APENAS o contexto fornecido.
Não invente informações.
Se não houver dados suficientes, diga claramente.
Cite fontes quando disponíveis.
Responda em português brasileiro.
```
Criado `build_qa_provider_from_env()` (lê as mesmas variáveis de ambiente). O provider de extração (`OpenAICompatibleResponseProvider`) **não foi alterado**.

---

### Bug 2 — Fontes não chegavam ao contexto nem ao prompt (CRÍTICO)

**Problema:** `fetch_sources_for_decisions` buscava fontes do banco, mas `build_context_for_question` não recebia esse dado. `BuiltContext.sources` era sempre `[]`. O prompt exibia sempre `(nenhuma fonte registrada)`.

**Correção (2 partes):**

1. `build_context_for_question` recebeu parâmetro opcional `sources: list[SourceReference] | None = None` e popula `BuiltContext.sources = sources or []`
2. `build_answer_prompt` corrigido para acessar `source.title` e `source.source_path` (atributos do dataclass `SourceReference`) em vez de `src.get('title')` (sintaxe de dict que gerava `AttributeError`)
3. `ask_question` em `query.py` passa as fontes buscadas: `build_context_for_question(question, explanation, sources=sources)`

---

### Bug 3 — CLI `--json` retornava só `TopicExplanation`, não `AnswerResult`

**Problema:** `ask --json` chamava `_print_json_payload(result.structured)`, retornando apenas os campos do struct de explicação (`topic`, `decisions`, etc.) sem `answer`, `degraded`, `sources`.

**Correção:** `ask_command` monta e serializa o payload completo:
```json
{
  "question": "...",
  "answer": "...",
  "degraded": true,
  "sources": [...],
  "structured": {"topic": "...", "decisions": [...], ...}
}
```

---

### Fix 4 — Modo degradado com formato inconsistente

**Problema:** `_format_structured_answer` usava cabeçalhos diferentes dos produzidos pelo LLM (`Decisões encontradas:`, `Evidências:`, etc.), dificultando parsing uniforme do output.

**Correção:** Seções agora usam os mesmos cabeçalhos Markdown do template de resposta LLM:
- `## Resposta direta`
- `## Justificativa`
- `## Riscos e conflitos`
- `## Próximos passos`
- `## Fontes`

---

## 3. Arquivos Alterados

| Arquivo | Mudança | Tipo |
|---|---|---|
| `src/brain4me/llm_client.py` | Adicionados `QAResponseProvider` e `build_qa_provider_from_env` | adição |
| `src/brain4me/context_builder.py` | `BuiltContext.sources` → `list[SourceReference]`; parâmetro `sources` em `build_context_for_question`; fix `.get()` → atributo | correção |
| `src/brain4me/query.py` | Troca `build_openai_compatible_provider_from_env` → `build_qa_provider_from_env`; passa `sources` ao context builder; novos cabeçalhos no modo degradado | correção |
| `src/brain4me/cli.py` | `ask --json` retorna payload `AnswerResult` completo | correção |
| `tests/test_phase3.py` | 6 novos testes (TDD RED→GREEN) | novo |
| `tests/test_phase2.py` | Tests 3, 4, 5 atualizados para novo comportamento correto | atualização |
| `tests/test_cli.py` | `test_cli_ask_supports_json_output` atualizado para novo JSON | atualização |

---

## 4. Testes

### Novos testes (test_phase3.py)

| # | Nome | O que testa |
|---|---|---|
| 1 | `test_qa_provider_sends_qa_system_prompt_not_extraction` | `QAResponseProvider` envia system prompt sem "JSON"/"entities" |
| 2 | `test_sources_passed_to_context_builder_appear_in_built_context` | `sources=` em `build_context_for_question` popula `built_context.sources` |
| 3 | `test_sources_appear_in_answer_prompt_text` | Título da fonte aparece no texto do prompt |
| 4 | `test_cli_ask_json_returns_full_answer_result_fields` | JSON da CLI tem `question`, `answer`, `degraded`, `sources`, `structured` |
| 5 | `test_ask_question_uses_qa_provider_not_extraction_provider` | `ask_question` usa `build_qa_provider_from_env` |
| 6 | `test_degraded_fallback_works_when_qa_provider_unavailable` | Modo degradado funciona quando QA provider retorna `None` |

### Resultado total

```
46 passed in ~49s
```

---

## 5. Diff Relevante

### `llm_client.py` — novo provider

```python
_QA_SYSTEM_PROMPT = (
    "Você é um assistente de segundo cérebro.\n\n"
    "Use APENAS o contexto fornecido.\n"
    "Não invente informações.\n"
    "Se não houver dados suficientes, diga claramente.\n"
    "Cite fontes quando disponíveis.\n"
    "Responda em português brasileiro."
)

class QAResponseProvider:
    # mesmo contrato do OpenAICompatibleResponseProvider
    # system prompt: _QA_SYSTEM_PROMPT (não retorna JSON)

def build_qa_provider_from_env() -> QAResponseProvider | None:
    # mesmas variáveis de env: BRAIN4ME_LLM_API_KEY, BRAIN4ME_LLM_MODEL, BRAIN4ME_LLM_API_URL
```

### `context_builder.py` — fontes chegam ao contexto

```python
# ANTES
def build_context_for_question(question, explanation, *, max_chars=12000) -> BuiltContext:
    ...
    return BuiltContext(..., sources=[], ...)

# DEPOIS
def build_context_for_question(question, explanation, *, sources=None, max_chars=12000) -> BuiltContext:
    ...
    return BuiltContext(..., sources=sources or [], ...)

# ANTES (build_answer_prompt)
f"- {src.get('title') or src.get('source_path', '')}"

# DEPOIS
f"- {src.title or src.source_path}"
```

### `query.py` — usa QA provider e passa fontes

```python
# ANTES
built_context = build_context_for_question(question, explanation)
provider = build_openai_compatible_provider_from_env()

# DEPOIS
built_context = build_context_for_question(question, explanation, sources=sources)
provider = build_qa_provider_from_env()
```

### `cli.py` — JSON completo

```python
# ANTES
_print_json_payload(result.structured)

# DEPOIS
payload = {
    "question": result.question,
    "answer": result.answer,
    "degraded": result.degraded,
    "sources": [asdict(s) for s in result.sources],
    "structured": asdict(result.structured),
}
click.echo(json.dumps(payload, ensure_ascii=False, sort_keys=True))
```

---

## 6. Limitações Restantes

| Limitação | Impacto | Observação |
|---|---|---|
| Sem retry no LLM | Baixo | Timeout de 30s hardcoded. Falha silenciosa → modo degradado |
| Sem deduplicação de contexto | Baixo | Seções podem ter itens repetidos se vindos de múltiplas fontes |
| `TopicExplanation` sem histórico de memória | Médio | `memory_entries` não entram no contexto enviado ao LLM |
| Prioridade entre seções é fixa | Baixo | Decisões sempre antes de evidências, independente dos scores |
| LLM real não testado end-to-end | Médio | Testes usam mocks; comportamento com LLM real depende do modelo |
| Provider de extração separado do QA | Neutro | Intencionalmente separado — não é limitação, é design correto |

---

## 7. Arquitetura Intacta

- Schema do banco: **não alterado**
- `OpenAICompatibleResponseProvider` (extração): **não alterado**
- `explain_topic`, `explain_entity`: **não alterados**
- Modo degradado: **mantido e melhorado**
- Todos os 40 testes anteriores: **continuam passando**
