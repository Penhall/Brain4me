# Roadmap

## Objetivo

Organizar a evolução do projeto em fases curtas, cumulativas e verificáveis. Cada fase deve produzir artefatos úteis, não apenas abrir novas frentes.

## Fase 0 — Fundação documental

### Entregáveis

- visão geral consolidada;
- conceitos fundamentais;
- ontologia base;
- arquitetura do MVP;
- modelo de dados;
- prompts operacionais.

### Critério de saída

Um desenvolvedor consegue iniciar a implementação sem redefinir o escopo conceitual.

## Fase 1 — Pipeline mínimo de ingestão

### Objetivo

Receber notas Markdown e persistir entidades, relações e fontes com rastreabilidade.

### Entregáveis

- parser inicial de Markdown;
- normalização de metadados;
- persistência relacional;
- deduplicação simples de entidades;
- registro de confiança e origem.

## Fase 2 — Grafo e consultas explicáveis

### Objetivo

Projetar grafos a partir do banco e responder perguntas com justificativa.

### Entregáveis

- materialização de subgrafos;
- recuperação por entidade, relação e decisão;
- formato padrão de resposta explicável;
- primeiras consultas analíticas.

## Fase 3 — Memória e contexto

### Objetivo

Adicionar recuperação contextual e histórico de decisões.

### Entregáveis

- memória semântica, episódica e procedural;
- políticas de promoção de memória;
- contexto por compartimento;
- revisão de respostas com base em histórico.

## Fase 4 — Agentes especializados

### Objetivo

Separar ingestão, curadoria, consulta e decisão em agentes com responsabilidades claras.

### Entregáveis

- orquestração básica entre agentes;
- auditoria de consistência;
- análise estruturada de decisões;
- logs e trilhas de revisão.

## Fase 5 — Evolução de infraestrutura

### Objetivo

Aumentar sofisticação sem perder explicabilidade.

### Entregáveis

- avaliação de migração para Neo4j;
- possível adoção de indexação vetorial complementar;
- regras mais ricas de ontologia;
- dashboards de exploração e revisão.

## Sinais de revisão de rumo

- o banco relacional já não atende travessias e consultas com clareza;
- o LLM está compensando falhas de modelagem, em vez de complementar o sistema;
- há excesso de memória irrelevante sendo recuperada;
- a ontologia está rígida demais para novos compartimentos.
