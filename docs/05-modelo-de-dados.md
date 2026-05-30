# Modelo de Dados

## Objetivo

Propor um modelo relacional inicial que suporte a ontologia base, preserve rastreabilidade e permita projetar grafos sem depender de um banco de grafo no MVP.

## Estratégia

O banco relacional guarda a verdade operacional. O grafo é derivado dessa base. Isso facilita:

- auditoria por SQL;
- evolução incremental do esquema;
- versionamento de regras e metadados;
- migração futura para motores mais especializados.

Nos exemplos abaixo, `SQLite` é a referência padrão do MVP. O esquema deve permanecer portátil o bastante para `DuckDB` caso o projeto priorize workloads analíticos.

## Entidades/tabelas principais

### `compartments`

Representa domínios ou subprojetos.

| Campo | Tipo lógico | Observação |
| --- | --- | --- |
| `id` | uuid/texto | chave primária |
| `slug` | texto | identificador estável |
| `name` | texto | nome legível |
| `description` | texto | objetivo do compartimento |
| `created_at` | datetime | auditoria |

### `sources`

Origem do conteúdo.

| Campo | Tipo lógico | Observação |
| --- | --- | --- |
| `id` | uuid/texto | chave primária |
| `compartment_id` | fk | domínio principal |
| `source_type` | texto | `markdown`, `link`, `pdf`, `conversation` |
| `source_path` | texto | caminho ou URL |
| `title` | texto | título da fonte |
| `captured_at` | datetime | momento de entrada |
| `hash` | texto | deduplicação opcional |

### `notes`

Texto processável derivado da fonte.

| Campo | Tipo lógico | Observação |
| --- | --- | --- |
| `id` | uuid/texto | chave primária |
| `source_id` | fk | origem da nota |
| `content_markdown` | texto longo | conteúdo canônico |
| `summary` | texto | resumo opcional |
| `status` | texto | `raw`, `parsed`, `validated` |
| `created_at` | datetime | auditoria |

### `entities`

Nó semântico principal.

| Campo | Tipo lógico | Observação |
| --- | --- | --- |
| `id` | uuid/texto | chave primária |
| `compartment_id` | fk | contexto primário |
| `entity_type` | texto | `Concept`, `Project`, `Decision` etc. |
| `canonical_name` | texto | nome normalizado |
| `description` | texto | definição curta |
| `status` | texto | `draft`, `active`, `deprecated` |
| `confidence` | numérico | confiança da extração |
| `created_at` | datetime | auditoria |

### `entity_aliases`

Sinônimos e formas variantes.

| Campo | Tipo lógico | Observação |
| --- | --- | --- |
| `id` | uuid/texto | chave primária |
| `entity_id` | fk | entidade canônica |
| `alias` | texto | nome alternativo |
| `alias_type` | texto | `synonym`, `spelling`, `short_name` |

### `relations`

Arestas estruturadas entre entidades.

| Campo | Tipo lógico | Observação |
| --- | --- | --- |
| `id` | uuid/texto | chave primária |
| `subject_entity_id` | fk | origem |
| `predicate` | texto | `depende_de`, `suporta`, `afeta` |
| `object_entity_id` | fk | destino |
| `assertion_type` | texto | `fact`, `hypothesis`, `decision_context` |
| `confidence` | numérico | confiabilidade |
| `source_note_id` | fk | nota de origem |
| `created_at` | datetime | auditoria |

### `claims`

Camada textual explicável associada a uma relação ou entidade.

| Campo | Tipo lógico | Observação |
| --- | --- | --- |
| `id` | uuid/texto | chave primária |
| `note_id` | fk | origem textual |
| `entity_id` | fk opcional | foco da afirmação |
| `relation_id` | fk opcional | aresta relacionada |
| `claim_type` | texto | `evidence`, `risk`, `opportunity`, `constraint` |
| `content` | texto | enunciado legível |
| `confidence` | numérico | confiança |

### `decisions`

Registro formal de decisões.

| Campo | Tipo lógico | Observação |
| --- | --- | --- |
| `id` | uuid/texto | chave primária |
| `entity_id` | fk | entidade do tipo `Decision` |
| `problem_statement` | texto | problema que motivou a decisão |
| `chosen_option` | texto | alternativa escolhida |
| `status` | texto | `proposed`, `accepted`, `revised`, `deprecated` |
| `decided_at` | datetime | data da decisão |

### `decision_options`

Alternativas avaliadas.

| Campo | Tipo lógico | Observação |
| --- | --- | --- |
| `id` | uuid/texto | chave primária |
| `decision_id` | fk | decisão vinculada |
| `option_name` | texto | nome da alternativa |
| `pros` | texto | pontos a favor |
| `cons` | texto | pontos contra |
| `outcome` | texto | `chosen`, `rejected`, `deferred` |

### `memory_entries`

Memória persistente acessada por agentes.

| Campo | Tipo lógico | Observação |
| --- | --- | --- |
| `id` | uuid/texto | chave primária |
| `compartment_id` | fk | escopo |
| `memory_type` | texto | `semantic`, `episodic`, `procedural`, `working_snapshot` |
| `related_entity_id` | fk opcional | âncora |
| `content` | texto | item de memória |
| `valid_from` | datetime | início de validade |
| `valid_to` | datetime opcional | fim de validade |
| `priority` | inteiro | relevância para recuperação |

## Índices recomendados

- `entities(compartment_id, entity_type, canonical_name)`
- `relations(subject_entity_id, predicate, object_entity_id)`
- `sources(source_type, source_path)`
- `memory_entries(compartment_id, memory_type, priority)`
- `decisions(status, decided_at)`

## Projeção para grafo

O grafo pode ser montado assim:

- `entities` viram nós;
- `relations` viram arestas tipadas;
- `claims`, `decisions` e `memory_entries` entram como atributos ou nós auxiliares conforme a consulta.

## Exemplo mínimo

Uma decisão sobre banco do MVP pode ocupar:

- 1 registro em `entities` com tipo `Decision`;
- 1 registro em `decisions`;
- 2 registros em `decision_options` (`SQLite`, `Neo4j`);
- 1 ou mais registros em `claims` para riscos e justificativas;
- várias `relations` conectando a decisão ao projeto e aos objetivos impactados.
