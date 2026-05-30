# Decisões Arquiteturais

## ADR-001 — Markdown como entrada canônica

- `Status`: aceita
- `Contexto`: o sistema precisa de um formato simples, local, versionável e independente de fornecedor.
- `Decisão`: usar Markdown como formato principal de captura no MVP.
- `Trade-off`: ganha simplicidade e portabilidade, mas exige parser próprio para semântica rica.
- `Critério de revisão`: reavaliar se surgirem fontes predominantes não textuais ou fluxos block-based essenciais.

## ADR-002 — Banco relacional como verdade inicial

- `Status`: aceita
- `Contexto`: o projeto precisa de persistência rastreável com baixo custo operacional.
- `Decisão`: usar SQLite como armazenamento principal do MVP, preservando compatibilidade com DuckDB como alternativa analítica.
- `Trade-off`: simplifica setup e auditoria, mas desloca parte da lógica de grafo para projeções derivadas.
- `Critério de revisão`: revisar quando consultas relacionais e travessias ficarem complexas demais para manutenção simples.

## ADR-003 — Grafo derivado, não primário

- `Status`: aceita
- `Contexto`: o valor do projeto depende de conexões entre entidades, mas não exige banco de grafo logo no início.
- `Decisão`: projetar subgrafos com NetworkX a partir do banco relacional.
- `Trade-off`: reduz complexidade no curto prazo, porém pode limitar escala e persistência nativa de grafos.
- `Critério de revisão`: reavaliar com crescimento do volume de relações ou necessidade de exploração interativa avançada.

## ADR-004 — LLM como assistente

- `Status`: aceita
- `Contexto`: o LLM ajuda na extração e síntese, mas não pode comprometer auditabilidade.
- `Decisão`: usar LLM via API apenas para sugerir estrutura e redigir respostas, sempre com persistência de fontes e revisão por regras.
- `Trade-off`: melhora produtividade, mas exige controle para evitar alucinação semântica.
- `Critério de revisão`: revisar se a qualidade das heurísticas locais se mostrar suficiente para reduzir o uso do LLM.

## ADR-005 — Ontologia leve e evolutiva

- `Status`: aceita
- `Contexto`: o domínio ainda está em formação e envolve múltiplos compartimentos pessoais.
- `Decisão`: iniciar com poucos tipos e relações centrais, versionados e extensíveis.
- `Trade-off`: reduz atrito inicial, mas exige disciplina para não cair em relações genéricas demais.
- `Critério de revisão`: aprofundar a ontologia quando surgirem padrões estáveis de uso e consultas recorrentes.
