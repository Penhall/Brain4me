# Memória e Contexto

## Objetivo

Definir como o sistema preserva continuidade entre notas, consultas e decisões. Memória aqui não é log bruto; é conhecimento recuperável com utilidade operacional.

## Tipos de memória

### Memória semântica

Guarda fatos relativamente estáveis:

- conceitos;
- entidades canônicas;
- relações consolidadas;
- definições de domínio.

Exemplo: `SQLite é a persistência preferida do MVP atual`.

### Memória episódica

Guarda ocorrências situadas no tempo:

- reuniões;
- revisões de arquitetura;
- perguntas feitas;
- decisões datadas;
- mudanças de direção.

Exemplo: `em abril, a escolha por SQLite foi aceita para reduzir setup`.

### Memória procedural

Guarda como o sistema e o usuário preferem operar:

- critérios de decisão;
- fluxo de ingestão;
- regras de revisão;
- preferências de formatação ou classificação.

Exemplo: `decisões relevantes exigem justificativa e alternativa rejeitada`.

### Memória de trabalho

É temporária e voltada a uma consulta ou tarefa em andamento:

- entidades candidatas;
- subgrafo corrente;
- hipóteses de resposta;
- filtros ativos.

Ela pode ser descartada ao fim da operação, salvo se gerar aprendizado persistente.

## O que é contexto

Contexto é a seleção de memória e fatos relevantes para uma pergunta ou ação. Ele combina:

- compartimento atual;
- objetivo ativo;
- horizonte temporal;
- decisões relacionadas;
- riscos e restrições conhecidas.

Contexto não é o banco inteiro carregado de uma vez.

## Estratégia de armazenamento

| Tipo | Persistência sugerida | Uso principal |
| --- | --- | --- |
| semântica | `entities`, `relations`, `claims` | consulta e análise |
| episódica | `notes`, `sources`, `decisions`, `events` | histórico e rastreabilidade |
| procedural | `memory_entries` + regras em `JSON/YAML` | governança do sistema |
| trabalho | snapshot temporário em memória ou tabela efêmera | execução de consulta |

## Política inicial de recuperação

1. recuperar primeiro o compartimento mais provável;
2. incluir decisões e objetivos conectados ao tema;
3. priorizar memória recente quando a pergunta for operacional;
4. priorizar memória consolidada quando a pergunta for conceitual;
5. anexar conflitos relevantes, não apenas confirmações.

## Política de consolidação

Nem toda interação deve virar memória durável. Um item deve ser promovido quando:

- influencia decisões futuras;
- corrige entendimento anterior;
- se repete em múltiplas notas;
- vira regra de operação;
- representa preferência estável do usuário.

## Riscos de memória mal gerida

- excesso de contexto irrelevante;
- reforço de hipóteses fracas como se fossem fatos;
- repetição de decisões antigas fora de contexto;
- perda de rastreabilidade entre nota e conclusão.

## Princípio operacional

Memória útil é seletiva, tipada e recuperável. Guardar tudo sem hierarquia produz ruído; guardar pouco demais destrói continuidade.
