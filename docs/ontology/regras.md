# Regras

## Objetivo

Registrar regras de validação e inferência leve que mantêm o modelo coerente no MVP.

## Regras de validação

1. Toda `Decisão` deve apontar para pelo menos uma `Evidência`, `Objetivo` ou `Problema`.
2. Toda `Hipótese` precisa de status explícito: `aberta`, `em_validacao`, `confirmada` ou `descartada`.
3. Toda relação deve ter `sujeito`, `predicado`, `objeto` e `fonte`.
4. `Risco` e `Oportunidade` não devem existir sem objeto impactado.
5. `relacionado_a` só pode ser usada quando nenhuma relação mais precisa for adequada.

## Regras de inferência leve

1. Se uma `Decisão` possui múltiplas `Evidências` de suporte e nenhuma contradição forte, ela pode ganhar status de maior confiança.
2. Se duas notas distintas apontam o mesmo `Conceito` com aliases equivalentes, o sistema pode sugerir mesclagem.
3. Se uma decisão é marcada como `revisada`, memórias derivadas dela precisam ser reavaliadas.
4. Se uma hipótese é descartada, relações derivadas dela devem ser sinalizadas como obsoletas.

## Regras de governança

- não promover memória episódica a semântica sem recorrência ou confirmação;
- não transformar resumo de LLM em fato consolidado sem vínculo a fonte;
- registrar condição de revisão para decisões estratégicas;
- manter compatibilidade entre nome de relação e significado operacional.
