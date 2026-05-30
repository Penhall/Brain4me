# Ferramentas Chinesas e Asiáticas

## Objetivo

Avaliar ferramentas relevantes fora do eixo mais comum de open source ocidental, especialmente para knowledge base, RAG e modelagem semântica.

## Ferramentas observadas

| Ferramenta | Foco | Potencial para o projeto | Risco principal |
| --- | --- | --- | --- |
| SiYuan | PKM local-first | forte como referência de captura pessoal | extensibilidade profunda precisa validação |
| DB-GPT | LLM + dados | útil como referência de integração com bases | escopo amplo demais para o MVP |
| Dify | apps com LLM | boa referência de UX e orquestração | menor aderência à ontologia própria |
| FastGPT | chatbot/RAG | rápido para experimentos de consulta | sem foco forte em knowledge graph |
| MaxKB | base de conhecimento | pode inspirar camada de resposta | modelo semântico mais estreito |
| OpenSPG | semantic graph | alta relevância conceitual para grafos semânticos | adoção e operação mais complexas |

## Hipóteses

1. `SiYuan` é mais útil como inspiração de captura e organização pessoal do que como núcleo do sistema.
2. `OpenSPG` é conceitualmente valioso, mas pesado para a primeira iteração.
3. `Dify` e `DB-GPT` ajudam a entender padrões de produto, não necessariamente o núcleo da arquitetura.

## Lacunas

- falta benchmark prático de API/extensibilidade;
- falta comparar governança de dados e portabilidade;
- falta validar esforço real de customização para ontologia própria.
