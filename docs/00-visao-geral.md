# Projeto: Second Brain Semântico com Ontologia, Knowledge Graph e Context Graph

## 1. Visão inicial

Construir um sistema pessoal de conhecimento que funcione como um segundo cérebro avançado, capaz de armazenar conceitos, organizar conhecimento, conectar ideias, separar subprojetos e auxiliar na tomada de decisão com análises contextuais.

O projeto não deve ser apenas um app de notas. A proposta é criar uma camada inteligente de pensamento estruturado, combinando:

* Ontologias
* Grafos de conhecimento
* Grafos de contexto
* Sistema de memória
* Compartimentos por domínio/subprojeto
* Agentes de análise e decisão
* Integração futura com LLMs locais ou via API

## 2. Objetivo principal

Criar um sistema pessoal que permita responder perguntas como:

* O que eu já sei sobre este assunto?
* Quais conceitos estão relacionados?
* Que decisões anteriores se conectam com este problema?
* Quais padrões aparecem no meu histórico?
* Qual caminho parece mais coerente com meus objetivos?
* Quais riscos, oportunidades e contradições existem nessa decisão?

## 3. Ideia central

A arquitetura conceitual do projeto segue esta lógica:

```text
Notas / documentos / ideias
        ↓
Extração de conceitos
        ↓
Ontologia pessoal
        ↓
Knowledge Graph
        ↓
Context Graph
        ↓
Memória e análise
        ↓
Agente de decisão
```

## 4. Camadas do sistema

### 4.1 Camada de captura

Responsável por receber informações brutas:

* Notas pessoais
* Ideias soltas
* PDFs
* Links
* Resumos
* Conversas
* Decisões tomadas
* Projetos em andamento
* Estudos
* Conteúdo técnico

### 4.2 Camada de organização por compartimentos

O sistema deve permitir separar conhecimento em domínios ou subprojetos, por exemplo:

* Estudos
* Trabalho
* Projetos de IA
* Power BI
* Finanças pessoais
* Saúde
* Relacionamentos
* Filosofia
* Desenvolvimento de software
* Decisões estratégicas

Cada compartimento pode ter sua própria ontologia, regras, memória e contexto.

### 4.3 Camada de ontologia

Define os conceitos principais de cada domínio.

Exemplos de entidades:

* Conceito
* Pessoa
* Projeto
* Decisão
* Objetivo
* Problema
* Evidência
* Hipótese
* Regra
* Risco
* Oportunidade
* Fonte
* Evento
* Tarefa

Exemplos de relações:

* pertence_a
* depende_de
* contradiz
* reforça
* causa
* influencia
* é_evidência_de
* é_risco_para
* é_oportunidade_para
* foi_decidido_por
* está_relacionado_a

### 4.4 Camada de Knowledge Graph

Representa entidades e relações explícitas.

Exemplo:

```text
Projeto Petto → usa → agentes de IA
Agentes de IA → dependem de → memória
Memória → pode ser estruturada como → knowledge graph
```

### 4.5 Camada de Context Graph

Registra o porquê das relações, decisões e interpretações.

Exemplo:

```text
Decisão: usar Logseq como camada inicial
Motivo: já oferece notas locais, backlinks e grafo
Risco: pode limitar customização futura
Alternativa: criar interface própria desde o início
Conclusão: usar como protótipo, não como dependência definitiva
```

### 4.6 Camada de memória

A memória deve guardar:

* Preferências pessoais
* Histórico de decisões
* Aprendizados recorrentes
* Padrões observados
* Projetos ativos
* Fontes importantes
* Conceitos dominados
* Conceitos frágeis
* Erros e correções anteriores

### 4.7 Camada de análise e decisão

Responsável por transformar conhecimento em avaliação.

Tipos de análise desejados:

* Análise de prós e contras
* Análise de risco
* Análise de coerência com objetivos
* Análise de contradições
* Análise de custo-benefício
* Comparação entre alternativas
* Sugestão de próximos passos
* Revisão de decisões passadas

## 5. Projetos open source a investigar

### Captura e notas

* Logseq
* Obsidian-like open source alternatives
* AppFlowy
* Anytype
* SiYuan
* Trilium Notes

### Knowledge graph / graph database

* Neo4j Community
* ArangoDB
* TerminusDB
* TypeDB
* Apache Jena
* RDF4J

### Memória para agentes

* MemGPT / Letta
* LangGraph memory
* Zep
* OpenMemory
* Graphiti

### RAG e indexação

* LlamaIndex
* LangChain
* Haystack
* txtai

### Projetos chineses / asiáticos a investigar

* SiYuan
* OpenSPG
* DB-GPT
* FastGPT
* MaxKB
* Dify
* AnythingLLM alternatives chinesas
* Projetos de knowledge graph extraction em GitHub/Gitee

## 6. Direção técnica inicial

Para MVP, evitar complexidade excessiva.

Stack sugerida inicial:

* VS Code
* Python
* SQLite ou DuckDB
* NetworkX ou Neo4j Community
* Markdown como formato de entrada
* JSON/YAML para ontologias e regras
* LLM via API inicialmente
* Possível evolução para .NET/C# depois

## 7. MVP inicial

O MVP deve fazer apenas o essencial:

1. Criar compartimentos de conhecimento
2. Receber notas em Markdown
3. Extrair entidades e relações
4. Salvar conceitos em banco simples
5. Construir grafo inicial
6. Permitir consulta por pergunta
7. Gerar resposta com explicação baseada no grafo
8. Registrar decisões e motivos

## 8. Exemplo de uso

Entrada:

```text
Quero decidir se devo usar Neo4j ou SQLite no MVP do meu second brain.
```

Resposta esperada:

```text
Com base no objetivo atual de criar um MVP simples, SQLite parece mais adequado no início.

Motivos:
- menor complexidade
- mais fácil de versionar
- suficiente para entidades, relações e decisões básicas

Neo4j pode entrar depois, quando o grafo crescer ou quando consultas relacionais complexas forem necessárias.

Decisão sugerida:
Começar com SQLite + tabelas de entidades/relações/contextos e manter uma camada de abstração para futura migração para Neo4j.
```

## 9. Fases propostas

### Fase 1 — Pesquisa e benchmarking

Objetivo: mapear ferramentas open source que podem acelerar o projeto.

Entregáveis:

* Lista de projetos relevantes
* Avaliação de maturidade
* Licença
* Linguagem/stack
* Pontos fortes
* Limitações
* Possibilidade de reaproveitamento

### Fase 2 — Definição conceitual

Objetivo: definir claramente o que o sistema é e o que não é.

Entregáveis:

* Visão do produto
* Casos de uso
* Personas de uso pessoal
* Domínios iniciais
* Ontologia base
* Tipos de memória
* Tipos de análise

### Fase 3 — Arquitetura MVP

Objetivo: desenhar a primeira versão implementável.

Entregáveis:

* Arquitetura técnica
* Estrutura de pastas
* Modelo de dados
* Formato dos arquivos
* Fluxo de ingestão
* Fluxo de consulta
* Estratégia de persistência

### Fase 4 — Prompt mestre para desenvolvimento

Objetivo: criar um prompt completo para desenvolver no VS Code com Codex.

Entregáveis:

* Prompt mestre
* Regras de desenvolvimento
* Escopo do MVP
* Tarefas por etapa
* Critérios de aceite
* Stack final
* Instruções de implementação

## 10. Princípios do projeto

* Local-first sempre que possível
* Simplicidade antes de sofisticação
* Dados exportáveis
* Sem dependência fechada no começo
* Ontologia leve, evolutiva e prática
* Decisões explicáveis
* Separação clara entre conhecimento, contexto e memória
* MVP funcional antes de arquitetura perfeita
