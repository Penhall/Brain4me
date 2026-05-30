# Relações

## Objetivo

Definir relações semânticas reutilizáveis e evitar o uso excessivo de conexões genéricas.

## Relações principais

| Relação | Uso | Exemplo |
| --- | --- | --- |
| `pertence_a` | associa entidade ao compartimento | `Projeto Brain4me -> pertence_a -> Projetos de IA` |
| `originado_em` | liga estrutura à sua fonte | `Decisão SQLite -> originado_em -> nota-arquitetura.md` |
| `depende_de` | dependência estrutural ou operacional | `Pipeline de consulta -> depende_de -> memória semântica` |
| `suporta` | evidência favorável | `Benchmark local -> suporta -> decisão SQLite` |
| `contradiz` | oposição explícita | `Necessidade de travessia complexa -> contradiz -> manter apenas SQL` |
| `influencia` | efeito indireto | `Objetivo de simplicidade -> influencia -> escolha do banco` |
| `afeta` | efeito direto | `Decisão de stack -> afeta -> arquitetura MVP` |
| `resolve` | conexão com problema | `Decisão SQLite -> resolve -> problema de setup pesado` |
| `alternativa_a` | opção comparada | `Neo4j -> alternativa_a -> decisão banco MVP` |
| `deriva_de` | genealogia conceitual | `Hipótese de migração -> deriva_de -> benchmark inicial` |
| `precede` | ordem temporal ou lógica | `Pesquisa de stack -> precede -> decisão arquitetural` |
| `relacionado_a` | associação ampla quando nada melhor existir | usar só como último recurso |

## Diretrizes de uso

- prefira relações específicas a `relacionado_a`;
- use direção consistente sempre que possível;
- não misture `suporta` com `influencia`;
- `contradiz` deve indicar conflito real, não simples diferença.

## Relações típicas por tipo

- `Decisão` costuma `resolver`, `afetar`, `depender_de` e ser `suportada` por evidências.
- `Hipótese` costuma ser `suportada` ou `contradita`.
- `Risco` e `Oportunidade` costumam `afetar` projetos, objetivos ou decisões.
- `Projeto` costuma `depender_de` conceitos, recursos e tarefas.
