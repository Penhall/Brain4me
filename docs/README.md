# Documentação do Projeto

Este diretório reúne a documentação conceitual, técnica e estratégica do projeto de Second Brain Semântico com ontologias, knowledge graph, context graph, memória e agentes de decisão.

## Estrutura

- `00-visao-geral.md`: visão inicial do projeto
- `01-benchmark-opensource.md`: pesquisa de ferramentas open source
- `03-ontologia-base.md`: entidades, relações e regras iniciais
- `04-arquitetura-mvp.md`: arquitetura da primeira versão
- `11-prompt-mestre-codex.md`: prompt final para desenvolvimento com VS Code + Codex

## Como navegar

Sugestão de leitura para quem está entrando no projeto:

1. `00-visao-geral.md`: intenção do produto, princípios e limites do MVP.
2. `02-conceitos-fundamentais.md`: definição dos termos centrais usados no restante da documentação.
3. `03-ontologia-base.md` e pasta `ontology/`: modelo semântico inicial.
4. `04-arquitetura-mvp.md` até `09-agentes-e-decisoes.md`: desenho técnico do MVP.
5. `10-roadmap.md`: evolução planejada.
6. `11-prompt-mestre-codex.md` e pasta `prompts/`: material para execução futura com agentes.

## Pastas auxiliares

- `architecture/`: ADRs, diagramas e trade-offs.
- `ontology/`: detalhamento operacional da ontologia.
- `research/`: benchmark, hipóteses e lacunas de mercado/stack.
- `prompts/`: prompts reutilizáveis para planejamento, desenvolvimento e análise.

## Convenções usadas

- O fluxo principal do projeto é: `Notas -> Conceitos -> Ontologia -> Grafo -> Contexto -> Memória -> Decisão`.
- O MVP assume `Python`, `SQLite` como persistência padrão, `DuckDB` como alternativa analítica, entrada em `Markdown`, regras em `JSON/YAML` e projeção inicial de grafo com `NetworkX`.
- Sempre que possível, decisões arquiteturais devem ser registradas em `architecture/decisoes-arquiteturais.md`.

## Prompts disponíveis

- `prompts/prompt-planejamento.md`: preparação de escopo e execução.
- `prompts/prompt-desenvolvimento.md`: implementação alinhada à arquitetura.
- `prompts/prompt-revisao-codigo.md`: revisão técnica com foco no MVP.
- `prompts/prompt-geracao-ontologia.md`: extensão semântica incremental.
- `prompts/prompt-analise-decisao.md`: comparação de alternativas com contexto.

## Estado atual

Esta documentação prepara a implementação do MVP, mas não inicia código ainda. O objetivo aqui é reduzir ambiguidade para que a próxima etapa de desenvolvimento com Codex seja direta, incremental e explicável.
