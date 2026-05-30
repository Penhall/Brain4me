# Diagramas

## Visão sistêmica do MVP

```mermaid
flowchart LR
    N[Notas e Fontes] --> P[Parser]
    P --> X[Extracao Semantica]
    X --> O[Validacao Ontologica]
    O --> R[(SQLite padrao / DuckDB opcional)]
    R --> G[Subgrafo com NetworkX]
    R --> M[Memoria e Contexto]
    G --> Q[Orquestrador de Consulta]
    M --> Q
    Q --> A[Agente de Resposta]
```

## Fluxo de ingestão

```mermaid
flowchart TD
    A[Captura da Nota] --> B[Normalizacao]
    B --> C[Segmentacao]
    C --> D[Extracao de Entidades e Relacoes]
    D --> E[Resolucao de Duplicidade]
    E --> F[Validacao Ontologica]
    F --> G[Persistencia]
    G --> H[Atualizacao de Memoria]
```

## Fluxo de consulta explicável

```mermaid
flowchart TD
    U[Pergunta] --> I[Interpretacao de Intencao]
    I --> S[Selecao de Escopo]
    S --> D[Busca Estruturada]
    D --> G[Montagem de Subgrafo]
    G --> C[Recuperacao de Contexto]
    C --> R[Sintese Explicavel]
    R --> O[Resposta + Fontes + Riscos]
```

## Trade-offs resumidos

| Tema | Escolha atual | Benefício | Custo |
| --- | --- | --- | --- |
| entrada | Markdown | simples, portátil e versionável | semântica precisa ser extraída |
| persistência | SQLite padrão / DuckDB opcional | baixa complexidade operacional | grafo nativo ausente |
| grafo | NetworkX derivado | rápido para protótipo | sem persistência dedicada |
| inteligência | LLM assistivo | acelera extração e síntese | exige validação contra alucinação |
