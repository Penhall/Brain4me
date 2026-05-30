# Entidades

## Objetivo

Detalhar as entidades da ontologia base com atributos mínimos para implementação do MVP.

## Entidades nucleares

### Compartimento

- representa um domínio ou subprojeto;
- delimita contexto principal, regras e memória prioritária.

Atributos sugeridos:

- `nome`
- `slug`
- `descricao`
- `status`

### Fonte

- origem do conhecimento capturado;
- pode ser nota, link, PDF ou conversa.

Atributos sugeridos:

- `tipo`
- `caminho_ou_url`
- `titulo`
- `data_captura`

### Nota

- unidade textual processável;
- carrega o conteúdo bruto que gera estrutura.

Atributos sugeridos:

- `titulo`
- `conteudo_markdown`
- `resumo`
- `status_processamento`

### Conceito

- representa ideia, termo técnico ou abstração de domínio.

Atributos sugeridos:

- `nome_canonico`
- `descricao_curta`
- `aliases`
- `nivel_de_confianca`

### Projeto

- iniciativa contínua com objetivos e decisões associadas.

Atributos sugeridos:

- `nome`
- `objetivo`
- `estado`
- `compartimento_principal`

### Objetivo

- estado desejado que orienta decisões.

Atributos sugeridos:

- `descricao`
- `prioridade`
- `horizonte`
- `status`

### Problema

- questão aberta que demanda análise ou decisão.

Atributos sugeridos:

- `enunciado`
- `contexto`
- `urgencia`
- `status`

### Hipótese

- afirmação provisória que ainda depende de validação.

Atributos sugeridos:

- `descricao`
- `status_validacao`
- `confianca`
- `fonte_principal`

### Evidência

- suporte ou contraponto para hipótese ou decisão.

Atributos sugeridos:

- `descricao`
- `tipo`
- `forca`
- `origem`

### Decisão

- escolha registrada com justificativa.

Atributos sugeridos:

- `problema_associado`
- `opcao_escolhida`
- `status`
- `data_decisao`

### Alternativa

- opção considerada no processo decisório.

Atributos sugeridos:

- `nome`
- `pros`
- `contras`
- `resultado`

### Risco

- consequência negativa possível.

Atributos sugeridos:

- `descricao`
- `probabilidade`
- `impacto`
- `mitigacao`

### Oportunidade

- ganho potencial associado a uma decisão ou contexto.

Atributos sugeridos:

- `descricao`
- `impacto_esperado`
- `condicao`

### Regra

- restrição ou inferência declarativa.

Atributos sugeridos:

- `nome`
- `descricao`
- `tipo`
- `escopo`

## Observação prática

Nem toda entidade precisa virar uma tabela própria no MVP. Algumas podem ser modeladas como `entity_type` em uma tabela genérica, com detalhes complementares em tabelas específicas quando a necessidade aparecer.
