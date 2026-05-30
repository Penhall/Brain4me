````md
Você atuou na primeira grande fase de implementação do projeto Brain4me.

Agora gere um relatório técnico de avaliação para revisão externa pelo ChatGPT.

Não altere arquivos. Apenas analise o repositório atual e responda em Markdown.

## 1. Resumo executivo

Explique, em até 10 linhas:
- o que foi implementado;
- quais módulos existem;
- qual parte do MVP já funciona;
- quais limitações ainda permanecem.

## 2. Estrutura atual do projeto

Liste a árvore atual do projeto, no formato:

```text
brain4me/
├── ...
````

Inclua apenas arquivos relevantes.

## 3. Arquivos criados ou modificados

Crie uma tabela com:

| Arquivo | Finalidade | Status |
| ------- | ---------- | ------ |

Status possíveis:

* implementado
* parcial
* placeholder
* pendente

## 4. Banco de dados

Descreva o schema SQLite implementado.

Inclua:

* tabelas criadas;
* campos principais;
* chaves primárias;
* chaves estrangeiras;
* índices;
* quais tabelas dão suporte ao Knowledge Graph;
* quais tabelas dão suporte ao Context Graph.

Inclua também o DDL real ou resumido das tabelas principais.

## 5. Knowledge Graph

Explique como o Knowledge Graph foi implementado.

Responder obrigatoriamente:

* Qual arquivo implementa o KG?
* Ele usa NetworkX?
* Quais tabelas alimentam o grafo?
* Quais nós são criados?
* Quais arestas são criadas?
* Como o grafo diferencia entidade, relação e fonte?
* Há testes cobrindo isso?

## 6. Context Graph

Explique como o Context Graph foi implementado.

Responder obrigatoriamente:

* Qual arquivo implementa o Context Graph?
* Ele é realmente separado do Knowledge Graph?
* Quais tabelas alimentam o Context Graph?
* Quais nós são criados?
* Quais arestas são criadas?
* Como decisões, contextos, evidências e conflitos aparecem no grafo?
* Há teste demonstrando que KG e Context Graph são distintos?

## 7. Scoring e qualidade de fonte

Explique o que foi implementado sobre:

* score;
* confidence;
* source reliability;
* source type;
* priorização de contexto.

Diga claramente o que está funcional e o que ainda é apenas campo no banco.

## 8. Ingestão

Explique o pipeline de ingestão atual.

Responder:

* Markdown parser existe?
* Extractor existe?
* O extractor usa mock, heurística ou LLM?
* Há fallback para JSON inválido?
* Há checksum SHA256?
* Há transação no banco?
* Há linker de entidades duplicadas?
* Há geração de contexto automática?

## 9. Consulta

Explique o que existe do fluxo de consulta.

Responder:

* `brain ask` existe?
* Como entidades são recuperadas?
* Como o subgrafo é montado?
* Como contexto é ranqueado?
* A resposta cita fontes?
* O LLM já está integrado ou ainda é mock/pendente?

## 10. CLI

Liste os comandos CLI implementados e o status de cada um:

| Comando | Status | Observação |
| ------- | ------ | ---------- |

Comandos esperados:

* brain ingest
* brain ask
* brain decide
* brain log
* brain fact
* brain explain
* brain review decisions
* brain memory episodes
* brain memory patterns
* brain curate
* brain export

## 11. Testes

Liste os testes existentes.

Inclua:

* caminho do teste;
* o que ele valida;
* se cobre fluxo unitário ou integração;
* como executar;
* resultado atual da suíte.

## 12. Decisões técnicas tomadas

Liste as principais decisões tomadas na implementação.

Para cada uma:

| Decisão | Motivo | Trade-off |
| ------- | ------ | --------- |

## 13. Lacunas conhecidas

Liste tudo que ainda falta ou está parcial.

Separe em:

* crítico;
* importante;
* futuro.

## 14. Riscos arquiteturais

Avalie riscos como:

* acoplamento excessivo;
* schema frágil;
* Context Graph virar apenas tabela auxiliar;
* duplicação de entidades;
* falta de rastreabilidade;
* excesso de dependência do LLM;
* testes insuficientes.

## 15. Próximos passos recomendados

Sugira a próxima fase de implementação em ordem.

A resposta deve ser objetiva, técnica e honesta.
Não faça propaganda do projeto.
Não omita problemas.
Não altere arquivos.

```
```
Use este prompt no Codex:

````md
Você está na Fase 2 do projeto Brain4me.

Objetivo desta fase:
Implementar o **Context Builder + integração do LLM no fluxo de consulta**, sem refatorar a arquitetura inteira.

## Contexto

O projeto já possui:

- SQLite funcional
- ingestão de Markdown
- entidades e relações
- Knowledge Graph
- Context Graph
- scoring
- CLI funcional
- `brain ask`
- `brain explain`
- `llm_client.py`
- testes existentes

Problema atual:
`brain ask` ainda não gera uma resposta inteligente. Ele apenas retorna dados estruturados. Agora ele deve montar contexto, enviar ao LLM e retornar resposta explicável com fontes.

---

## Regras importantes

- Não reescreva a arquitetura.
- Não remova funcionalidades existentes.
- Não quebre testes atuais.
- Não introduza LangChain, LangGraph, CrewAI ou frameworks pesados.
- Use o `llm_client.py` existente.
- Se o LLM falhar, retornar resposta estruturada em modo degradado.
- A resposta deve preservar rastreabilidade.
- Adicione testes.

---

## Tarefas

### 1. Criar `src/brain4me/context_builder.py`

Implemente um módulo responsável por montar contexto para consulta.

Ele deve receber os dados retornados por `explain_topic()` ou `explain_entity()` e produzir um objeto estruturado com:

- pergunta original;
- entidades relevantes;
- decisões relevantes;
- evidências;
- riscos;
- alternativas;
- histórico;
- conflitos;
- fontes;
- score agregado;
- texto final de contexto para prompt.

Crie pelo menos:

```python
@dataclass
class BuiltContext:
    question: str
    context_text: str
    sources: list[dict[str, str]]
    score: float
    degraded: bool = False
````

Função principal:

```python
def build_context_for_question(
    question: str,
    explanation: TopicExplanation | EntityExplanation,
    *,
    max_chars: int = 12000,
) -> BuiltContext:
    ...
```

Critérios:

* priorizar decisões;
* depois evidências;
* depois riscos;
* depois alternativas;
* depois histórico;
* depois conflitos;
* ordenar por score quando disponível;
* limitar tamanho por `max_chars`;
* nunca retornar contexto vazio se houver dados estruturados.

---

### 2. Adicionar fontes reais às respostas

Hoje `TopicExplanation` e `EntityExplanation` não carregam origem.

Atualize o mínimo necessário para incluir referências de fonte:

* `source_path`
* `title`
* `note_id`
* `entity_name` ou `context_label`

Pode ser usando nova dataclass:

```python
@dataclass
class SourceReference:
    note_id: str
    source_path: str
    title: str
    label: str
```

Critérios:

* não precisa citar trecho exato ainda;
* mas toda resposta gerada deve listar fontes usadas;
* ajustar queries em `query_helpers.py` para recuperar fontes quando possível.

---

### 3. Integrar LLM no `ask_question()`

Atualize `src/brain4me/query.py`.

Fluxo esperado:

1. recuperar explicação estruturada atual;
2. chamar `build_context_for_question`;
3. se houver LLM configurado, enviar prompt ao LLM;
4. retornar resposta sintetizada;
5. se LLM falhar ou não estiver configurado, retornar modo degradado estruturado.

Não remova o comportamento estruturado atual. Apenas acrescente campo de resposta sintetizada.

Pode criar nova dataclass:

```python
@dataclass
class AnswerResult:
    question: str
    answer: str
    degraded: bool
    sources: list[SourceReference]
    structured: TopicExplanation | EntityExplanation
```

---

### 4. Prompt do LLM para resposta

Crie uma função:

```python
def build_answer_prompt(question: str, context: BuiltContext) -> str:
    ...
```

O prompt deve instruir o LLM a:

* responder em português brasileiro;
* usar somente o contexto fornecido;
* não inventar;
* citar as fontes pelo título ou caminho;
* separar:

  * resposta direta;
  * justificativa;
  * riscos/conflitos;
  * próximos passos;
  * fontes consultadas.

Formato esperado:

```md
## Resposta direta

...

## Justificativa

...

## Riscos e conflitos

...

## Próximos passos

...

## Fontes

...
```

Se o contexto for insuficiente, o LLM deve dizer isso claramente.

---

### 5. Atualizar CLI `brain ask`

Atualize o comando `brain ask` para exibir:

* resposta sintetizada quando disponível;
* indicação de modo degradado quando o LLM não foi usado;
* fontes;
* resumo estruturado opcional.

Critérios:

* manter `--json`;
* no JSON, incluir:

  * `question`
  * `answer`
  * `degraded`
  * `sources`
  * `structured`

---

### 6. Testes obrigatórios

Adicione testes cobrindo:

1. `context_builder` monta contexto não vazio a partir de uma explicação.
2. `context_builder` respeita `max_chars`.
3. `ask_question` usa LLM mockado quando provider está disponível.
4. `ask_question` entra em modo degradado quando LLM falha.
5. `brain ask --json` inclui `answer`, `degraded`, `sources` e `structured`.
6. Fontes aparecem quando há nota associada.

Não use API real nos testes.

---

## Resultado esperado

Ao final, apresente:

* arquivos criados/alterados;
* testes adicionados;
* comando usado para rodar testes;
* limitações restantes.

## Não fazer agora

* Não implementar interface web.
* Não implementar embeddings.
* Não implementar agentes novos.
* Não migrar para Neo4j.
* Não refatorar todo o modelo.
* Não alterar radicalmente o schema.

```
