# Benchmark Open Source

## Objetivo

Mapear ferramentas que podem acelerar o MVP ou influenciar a arquitetura futura do Second Brain Semântico. O foco não é adotar uma plataforma inteira, e sim entender quais capacidades podem ser reaproveitadas: captura, estruturação semântica, memória, grafos e orquestração com LLM.

## Critérios de comparação

- aderência ao fluxo `nota -> conceito -> grafo -> contexto -> decisão`;
- operação local ou self-hosted;
- extensibilidade por API, plugins ou acesso ao banco;
- capacidade de modelar relações explícitas;
- suporte a histórico, contexto e explicabilidade;
- complexidade operacional para um MVP pessoal.

## Tabela comparativa

| Ferramenta | Categoria | Pontos fortes | Limitações para este projeto | Aderência ao MVP |
| --- | --- | --- | --- | --- |
| Logseq | notas/PKM | Markdown local, backlinks, grafo, comunidade madura | ontologia e regras fracas; pouca separação formal entre conhecimento e decisão | alta como front-end de captura |
| AppFlowy | workspace/notas | open source, UI moderna, colaboração | modelo semântico ainda limitado; foco em produtividade geral | média |
| SiYuan | notas/PKM | local-first, blocos, backlinks, bom suporte offline | ecossistema menos previsível para extensões profundas | alta para captura e organização pessoal |
| Anytype | knowledge workspace | modelo por objetos, coleções e relações | ecossistema e automação menos abertos para pipeline técnico fino | média |
| Trilium Notes | notas estruturadas | hierarquia flexível e scripts | UX e ecossistema menores; grafo menos central | média |
| Neo4j Community | banco de grafo | linguagem Cypher, ecossistema vasto, consultas relacionais fortes | adiciona infraestrutura cedo demais para o MVP | média, melhor para fase 2 |
| TerminusDB | grafo/documentos | versionamento de dados, schema, consultas orientadas a grafos | curva de adoção maior; menos comum em stacks pessoais | média |
| TypeDB | base semântica | modelo conceitual forte, inferência por regras | complexidade elevada e operação mais pesada | baixa no MVP, alta a longo prazo |
| ArangoDB | multi-modelo | documentos + grafos em um só motor | adiciona superfície operacional além do necessário | média |
| Apache Jena / RDF4J | RDF/ontologia | forte base semântica e interoperabilidade | maior complexidade, menos pragmático para MVP pessoal | baixa no início |
| NetworkX | biblioteca de grafo | simples, local, ótima para prototipagem | não é banco; persistência e consultas precisam apoio externo | alta no MVP |
| LlamaIndex | RAG/índices | abstrações para ingestão, recuperação e agentes | pode induzir acoplamento cedo; precisa governança | média/alta |
| LangChain | orquestração | ecossistema amplo, integrações abundantes | abstração excessiva e instabilidade de APIs em alguns fluxos | média |
| Haystack | busca/RAG | pipelines claros, busca híbrida | maior peso operacional para caso pessoal | média |
| txtai | embeddings/busca | simples para protótipos locais | menos foco em contexto decisório e ontologia | média |
| Dify | plataforma LLM | rápido para prototipar apps com LLM | pouco controle fino sobre ontologia e grafo nativos | média para interface experimental |
| DB-GPT | plataforma LLM/dados | integração com dados, agentes e chat | escopo amplo; pode ser pesado para MVP enxuto | média |
| FastGPT | plataforma RAG | boa velocidade de entrega e UX de chatbot | menos foco em modelagem semântica rica | média |
| MaxKB | base de conhecimento | voltado a knowledge base e resposta com LLM | modelo conceitual mais restrito | média |
| MemGPT / Letta | memória de agentes | abordagem explícita de memória e estado | não resolve sozinho ontologia, grafo e governança | alta como referência conceitual |
| Zep | memória conversacional | armazenamento estruturado de histórico e contexto | foco principal em chat, não em ontologia pessoal | média |
| Graphiti / OpenMemory | memória/grafo | conexão entre memória e estrutura relacional | ecossistema ainda em evolução | média |

## Leitura estratégica

### O que vale reutilizar já no MVP

- `Logseq` ou `SiYuan` como inspiração para captura em Markdown e backlinks.
- `NetworkX` como camada de projeção de grafo em memória.
- `LlamaIndex` apenas como referência de pipeline, sem centralizar a arquitetura nele.
- `MemGPT/Letta` e `Zep` como referência para separar memória episódica, semântica e operacional.

### O que deve entrar depois

- `Neo4j` quando consultas relacionais, auditoria de caminhos e exploração do grafo ficarem complexas demais para SQL + projeção em memória.
- `TypeDB` apenas se o projeto exigir inferência semântica declarativa mais forte que regras simples em JSON/YAML.
- plataformas completas como `Dify` e `DB-GPT` apenas se surgir necessidade de interface conversacional pronta.

## Recomendação inicial

Para o MVP, a melhor relação entre simplicidade e capacidade é:

1. `Markdown` como entrada canônica.
2. `SQLite` como persistência principal do MVP.
3. `DuckDB` como alternativa válida quando a prioridade for análise local mais intensa, sem virar padrão prematuro.
4. `NetworkX` para projeções de grafo e travessias locais.
5. `LLM via API` apenas na extração assistida e síntese explicável, nunca como fonte única da verdade.
