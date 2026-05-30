# Conceitos Fundamentais

## Objetivo deste documento

Definir os termos-base do projeto para evitar ambiguidade entre captura de notas, modelagem semântica, consultas e agentes. Estes conceitos são reutilizados nos documentos de ontologia, arquitetura, dados e prompts.

## Ontologia

Ontologia, neste projeto, é o conjunto explícito de tipos de entidades, relações e regras que descrevem como o conhecimento pode ser representado.

Ela responde perguntas como:

- que tipos de coisa existem no sistema;
- como essas coisas podem se relacionar;
- quais restrições tornam uma afirmação válida;
- quais inferências simples podem ser geradas.

Exemplo: `Decisão` pode `afetar` um `Projeto`; uma `Evidência` pode `suportar` ou `contradizer` uma `Hipótese`.

## Knowledge Graph

Knowledge Graph é a representação operacional das entidades e relações extraídas ou registradas. Ele guarda fatos estruturados, não necessariamente todo o contexto interpretativo.

Função no projeto:

- conectar conceitos dispersos;
- permitir navegação por relações;
- suportar consultas explicáveis;
- servir de base para análise de impacto e similaridade.

Exemplo: `Projeto Brain4me -> usa -> SQLite`.

## Context Graph

Context Graph registra o significado situacional dos fatos: por que algo foi decidido, em que momento, com quais premissas, riscos, alternativas e objetivos.

Enquanto o Knowledge Graph responde `o que se relaciona com o quê`, o Context Graph responde `em qual contexto isso faz sentido`.

Exemplo:

- `Decisão`: usar SQLite no MVP
- `Motivo`: reduzir complexidade operacional
- `Alternativa`: Neo4j
- `Risco`: migração futura de consultas

## Modelagem conceitual

Modelagem conceitual é o processo de transformar conteúdo bruto em estruturas semânticas utilizáveis. No projeto, isso inclui:

1. identificar entidades;
2. nomear relações;
3. definir granularidade adequada;
4. separar fato, hipótese, opinião e decisão;
5. atribuir evidência e origem.

Boa modelagem conceitual evita dois extremos: notas soltas sem semântica e formalismo excessivo que paralisa o MVP.

## Context engineering

Context engineering é o desenho deliberado de quais informações chegam a um agente em cada tarefa. Não se trata apenas de “mais contexto”, mas de “contexto correto, no momento correto”.

No Brain4me, isso significa:

- escolher o compartimento relevante;
- recuperar memória semântica útil;
- anexar decisões anteriores relacionadas;
- expor objetivos, riscos e restrições ativos;
- limitar ruído irrelevante.

Sem context engineering, o agente responde com baixa coerência, repete decisões já tomadas ou ignora conflitos conhecidos.

## Memória de agente

Memória de agente é a capacidade de persistir e recuperar estado relevante ao longo do tempo. Para este projeto, ela deve ser separada em tipos:

- `memória semântica`: fatos relativamente estáveis, como conceitos e relações;
- `memória episódica`: eventos, notas, decisões e interações datadas;
- `memória procedural`: regras, fluxos e preferências operacionais;
- `memória de trabalho`: contexto temporário de uma consulta ou tarefa.

## Distinções importantes

| Conceito | Unidade principal | Pergunta que responde |
| --- | --- | --- |
| Ontologia | tipos, relações, regras | “como este domínio pode ser representado?” |
| Knowledge Graph | fatos conectados | “o que está relacionado?” |
| Context Graph | justificativas e circunstâncias | “por que isso importa aqui?” |
| Memória | estado persistido e recuperável | “o que o sistema já aprendeu?” |
| Agente | processo decisório ou operacional | “o que fazer com esse conhecimento?” |

## Princípio prático

O projeto não busca uma ontologia universal. A meta é uma ontologia leve, evolutiva e útil para decisões reais. Formalização demais no início reduz velocidade; formalização de menos impede consultas confiáveis.
