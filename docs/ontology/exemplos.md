# Exemplos Aplicados

## Exemplo 1 — Escolha de banco para o MVP

Entrada textual:

> Para validar rápido o Brain4me, SQLite parece melhor que Neo4j. A vantagem é reduzir setup e manutenção. O risco é perder flexibilidade para consultas relacionais complexas no futuro.

Representação:

- `Projeto`: Brain4me
- `Problema`: escolher banco inicial do MVP
- `Decisão`: usar SQLite no MVP
- `Alternativa`: Neo4j
- `Evidência`: reduzir setup e manutenção
- `Risco`: limitar consultas relacionais complexas

Relações:

- `Decisão -> resolve -> Problema`
- `Evidência -> suporta -> Decisão`
- `Alternativa -> alternativa_a -> Decisão`
- `Risco -> afeta -> Projeto`

## Exemplo 2 — Organização por compartimento

Entrada textual:

> O projeto Brain4me deve ficar no compartimento Projetos de IA, mas sua ontologia pode reaproveitar conceitos do compartimento Desenvolvimento de Software.

Representação:

- `Compartimento`: Projetos de IA
- `Compartimento`: Desenvolvimento de Software
- `Projeto`: Brain4me
- `Conceito`: Ontologia

Relações:

- `Projeto -> pertence_a -> Compartimento Projetos de IA`
- `Conceito Ontologia -> relacionado_a -> Compartimento Desenvolvimento de Software`

## Exemplo 3 — Hipótese com evidência conflitante

Entrada textual:

> DuckDB pode simplificar análises locais, mas talvez complique integrações futuras com um banco de grafo dedicado.

Representação:

- `Hipótese`: DuckDB simplifica análises locais
- `Evidência`: bom suporte analítico local
- `Risco`: integração futura com grafo pode exigir adaptação

Relações:

- `Evidência -> suporta -> Hipótese`
- `Risco -> contradiz -> Hipótese` quando o risco impactar a adoção sem ressalvas
