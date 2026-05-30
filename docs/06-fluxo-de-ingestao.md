# Fluxo de Ingestão

## Objetivo

Transformar conteúdo bruto em conhecimento estruturado sem perder contexto, origem e nível de confiança. Ingestão aqui não é apenas importar texto: é produzir uma representação utilizável por consultas e agentes.

## Entrada esperada

O MVP parte de fontes em:

- `Markdown` como formato principal;
- links e referências externas;
- anotações de decisões;
- resumos de leitura;
- registros de reuniões ou conversas.

## Etapas do fluxo

### 1. Captura

A nota entra com metadados mínimos:

- título;
- compartimento;
- data;
- tipo de fonte;
- tags livres opcionais.

### 2. Normalização

O sistema padroniza:

- encoding;
- frontmatter, se existir;
- headings;
- links;
- blocos de citação;
- datas e identificadores explícitos.

Resultado: uma `Nota` canônica pronta para análise.

### 3. Segmentação

O conteúdo é quebrado em unidades úteis:

- seções;
- parágrafos;
- listas de decisão;
- trechos com evidência;
- itens de ação.

Isso reduz ambiguidade na extração e melhora rastreabilidade.

### 4. Extração semântica

Nesta etapa o sistema identifica:

- entidades;
- relações;
- hipóteses;
- decisões;
- riscos e oportunidades;
- referências a objetivos ou problemas.

A extração pode usar regras simples e apoio de LLM. O LLM sugere; a camada ontológica valida.

### 5. Resolução e deduplicação

Nem toda menção gera uma entidade nova. O pipeline precisa:

- comparar nomes canônicos e aliases;
- detectar termos já existentes no compartimento;
- decidir entre `criar`, `mesclar` ou `sinalizar para revisão`.

### 6. Validação ontológica

Antes de persistir:

- tipos inválidos são rejeitados;
- relações sem sujeito ou objeto são descartadas;
- decisões sem justificativa recebem flag de incompletude;
- assertivas sem fonte não entram como fato consolidado.

### 7. Persistência

O sistema grava:

- `sources` e `notes`;
- `entities` e `aliases`;
- `relations`;
- `claims` com riscos, evidências e oportunidades;
- `memory_entries` quando a informação merece reaproveitamento futuro.

### 8. Projeção de grafo

Após persistência, um subgrafo do compartimento pode ser materializado para:

- análise local;
- testes de coerência;
- preparação de consulta.

## Exemplo resumido

Nota de entrada:

> Decidi usar SQLite no MVP porque quero evitar custo operacional. Se o número de relações crescer muito, Neo4j volta para a pauta.

Saída esperada:

- `Decision`: usar SQLite no MVP
- `Evidence`: evitar custo operacional
- `Alternative`: Neo4j
- `Risk/Condition`: crescimento de relações pode exigir revisão
- relações entre decisão, projeto, evidência e alternativa

## Princípios de qualidade

- nenhuma asserção importante sem fonte;
- nenhuma decisão importante sem contexto;
- confiança sempre explícita quando houver inferência automática;
- revisão manual deve ser possível sem reprocessar tudo;
- ingestão idempotente sempre que possível.
