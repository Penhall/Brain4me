# Comparativo de Stack

## Objetivo

Comparar combinações de stack para o MVP e a evolução futura, com foco em custo operacional, auditabilidade e aderência ao modelo semântico do projeto.

## Critérios

- simplicidade de setup;
- clareza para persistir ontologia e contexto;
- facilidade de consulta e auditoria;
- caminho de evolução para grafos e memória;
- custo de manutenção individual.

## Opções avaliadas

| Opção | Composição | Vantagens | Limitações | Avaliação |
| --- | --- | --- | --- | --- |
| A | Python + SQLite + NetworkX | stack mínima, auditável, local-first | menos recursos nativos de grafo | recomendada para MVP |
| B | Python + DuckDB + NetworkX | boa análise tabular local, leitura eficiente | ecossistema de app transacional menor que SQLite | boa alternativa |
| C | Python + Neo4j | consultas relacionais fortes desde o início | setup e modelagem mais pesados | melhor para fase posterior |
| D | Python + TypeDB | modelo conceitual forte e inferência | complexidade alta para MVP pessoal | não recomendada agora |

## Hipóteses

1. A stack A entrega o melhor equilíbrio entre velocidade e governança.
2. DuckDB pode ser melhor que SQLite se o projeto priorizar análise local em lote.
3. Neo4j só se paga quando o grafo virar o eixo principal de exploração interativa.

## Lacunas

- falta medir volume esperado de notas e relações;
- falta testar custo real de projetar subgrafos a partir de SQL;
- falta validar o peso do LLM no pipeline de extração.
