# Ontologia Base

## Objetivo

Definir a ontologia mínima viável para representar conhecimento pessoal, contexto decisório e evolução de projetos no MVP. Esta base deve ser pequena o suficiente para implementação simples e rica o suficiente para produzir respostas explicáveis.

## Princípios da ontologia

- começar com poucos tipos centrais e especializar depois;
- separar fatos, interpretações e decisões;
- toda afirmação relevante deve apontar para uma origem;
- compartimentos delimitam contexto de domínio, não isolam totalmente o conhecimento;
- regras devem ser legíveis e versionáveis em `JSON/YAML`.

## Entidades centrais

| Entidade | Papel no sistema | Exemplos |
| --- | --- | --- |
| `Compartimento` | domínio ou subprojeto com contexto próprio | `Trabalho`, `Saúde`, `Brain4me` |
| `Fonte` | origem do conhecimento | nota Markdown, link, PDF, conversa |
| `Nota` | unidade textual capturada | resumo de reunião, reflexão, estudo |
| `Conceito` | ideia, termo ou objeto abstrato | `Knowledge Graph`, `LLM`, `MVP` |
| `Pessoa` | agente humano relevante | usuário, mentor, cliente |
| `Projeto` | iniciativa contínua | `Second Brain Semântico` |
| `Objetivo` | estado desejado | reduzir retrabalho, acelerar decisões |
| `Problema` | dor ou pergunta aberta | escolher banco do MVP |
| `Hipótese` | afirmação ainda não consolidada | DuckDB pode simplificar análise local |
| `Evidência` | suporte ou contraponto para uma hipótese/decisão | benchmark, experimento, nota |
| `Decisão` | escolha registrada | usar SQLite no MVP |
| `Alternativa` | opção comparada em uma decisão | Neo4j, DuckDB |
| `Risco` | efeito negativo possível | sobrecarga de migração futura |
| `Oportunidade` | ganho potencial | consulta relacional mais rica |
| `Regra` | restrição ou inferência explícita | decisão importante exige justificativa |
| `Evento` | ocorrência datada | revisão de arquitetura, mudança de stack |
| `Tarefa` | ação operacional | modelar parser de Markdown |

## Relações nucleares

| Relação | Origem -> Destino | Significado |
| --- | --- | --- |
| `pertence_a` | entidade -> compartimento | delimita o domínio principal |
| `originado_em` | entidade -> fonte/nota | informa proveniência |
| `relacionado_a` | entidade -> entidade | associação genérica, usar com parcimônia |
| `depende_de` | projeto/tarefa/decisão -> entidade | dependência estrutural |
| `suporta` | evidência -> hipótese/decisão | reforça uma afirmação |
| `contradiz` | evidência/hipótese -> hipótese/decisão | aponta conflito |
| `influencia` | entidade -> decisão/objetivo | impacto indireto |
| `afeta` | decisão/risco/oportunidade -> projeto/objetivo | consequência direta |
| `alternativa_a` | alternativa -> decisão | opção analisada |
| `resolve` | decisão/tarefa -> problema | indica resolução pretendida |
| `deriva_de` | conceito/hipótese -> conceito/nota | mostra genealogia conceitual |
| `precede` | evento/decisão -> evento/decisão | ordenação temporal lógica |

## Estrutura mínima de um registro semântico

Cada fato extraído do Markdown deve poder ser expresso com:

- `sujeito`;
- `predicado`;
- `objeto`;
- `tipo da asserção` (`fato`, `hipótese`, `decisão`, `risco`, `oportunidade`);
- `fonte`;
- `confiança`;
- `timestamp`;
- `compartimento`.

## Exemplo aplicado

Entrada textual:

> Para o MVP do Brain4me, SQLite parece melhor que Neo4j porque reduz complexidade operacional. O risco é limitar consultas relacionais avançadas no futuro.

Representação resumida:

- `Projeto: Brain4me`
- `Decisão: usar SQLite no MVP`
- `Alternativa: Neo4j`
- `Decisão -> afeta -> Projeto`
- `Evidência: reduz complexidade operacional`
- `Evidência -> suporta -> Decisão`
- `Risco: limita consultas relacionais avançadas`
- `Risco -> afeta -> Projeto`

## Regras semânticas iniciais

1. Toda `Decisão` relevante deve ter pelo menos um `Motivo/Evidência`.
2. Toda `Hipótese` deve carregar status: `aberta`, `em validação`, `confirmada` ou `descartada`.
3. Toda entidade derivada de texto deve apontar para uma `Fonte`.
4. Relações genéricas `relacionado_a` só devem existir quando nenhuma relação mais específica couber.
5. `Risco` e `Oportunidade` devem apontar para o objeto impactado.

## Limites deliberados do MVP

- não modelar ontologia formal completa em OWL/RDF nesta fase;
- não introduzir inferência complexa dependente de motor externo;
- não separar dezenas de subclasses prematuramente;
- não depender do LLM para validar a verdade de uma afirmação.
