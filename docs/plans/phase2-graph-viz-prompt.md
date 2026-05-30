# Fase 2: Visualização de grafo interativo (estilo InfraNodus)

## Contexto

Brain4me tem dois `nx.DiGraph` cacheados em `GraphCache` (Knowledge Graph + Context Graph) mas zero visualização. O Streamlit só mostra estatísticas textuais `"KG Nn/Ee"`. Queremos um grafo interativo estilo InfraNodus — force-directed, nós coloridos por tipo, arestas rotuladas, zoom/pan.

## Objetivo

Adicionar visualização de grafo interativa ao Streamlit app usando Sigma.js v2 embedado.

## Tarefas

### 1. Criar src/brain4me/graph_viz.py

Função principal:
```python
def build_graph_html(
    cache: GraphCache,
    highlight_entities: list[str] | None = None,
    height: int = 600,
) -> str:
```

Que:
- Converte `cache.kg` (nx.DiGraph) para JSON no formato esperado pelo Sigma.js
- Gera HTML completo com Sigma.js v2 via CDN + graphology-forceatlas2
- Layout ForceAtlas2 com parâmetros otimizados
- Nós coloridos por `entity_type` (ver paleta abaixo)
- Tamanho do nó proporcional a `score` (escala linear, min 4 max 20)
- Arestas com label (predicate) visível
- Espessura da aresta proporcional a `score`
- Interações: zoom (scroll), pan (drag), hover (destaca vizinhos), clique (tooltip)
- Se `highlight_entities` fornecido, destaca subgrafo com zoom automático
- Background escuro (#0e1117) para combinar com tema Streamlit

### 2. Paleta de cores por entity_type

```python
ENTITY_COLORS = {
    "Decision": "#ef4444",
    "Problem": "#f59e0b", 
    "Evidence": "#3b82f6",
    "Risk": "#dc2626",
    "Alternative": "#8b5cf6",
    "Hypothesis": "#ec4899",
    "Objective": "#10b981",
    "Opportunity": "#22c55e",
    "Project": "#6366f1",
}
```

### 3. Fontes CDN para Sigma.js

Usar CDN do jsDelivr:
```html
<script src="https://cdn.jsdelivr.net/npm/sigma@2.4.6/build/sigma.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/graphology@0.25.4/dist/graphology.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/graphology-layout-forceatlas2@0.11.0/dist/graphology-layout-forceatlas2.min.js"></script>
```

### 4. Modificar app.py

Após a resposta da query (linha ~153), adicionar seção de grafo:

```python
# Após a resposta, adicionar visualização do grafo
if result is not None:
    from brain4me.graph_viz import build_graph_html
    from brain4me.graph_cache import get_cached_graphs
    
    cache = get_cached_graphs(db_path)
    if cache.kg and cache.kg.number_of_nodes() > 0:
        with st.expander("🗺️ Knowledge Graph", expanded=False):
            entities = result.detected_entities if result.detected_entities else None
            graph_html = build_graph_html(cache, highlight_entities=entities)
            st.components.v1.html(graph_html, height=620, scrolling=False)
```

### 5. Atualizar __init__.py

Exportar `build_graph_html`.

## Design notes

- Sigma.js v2 usa graphology por baixo. Precisamos criar um `graphology.Graph` no JS a partir do JSON
- O formato de entrada é `{nodes: [{key, attributes: {label, entity_type, score, ...}}], edges: [{source, target, attributes: {predicate, score, ...}}]}`
- ForceAtlas2 precisa de algumas iterações (~100) para convergir — executar no JS após carregar
- Tooltip no hover: mostrar `label` + `entity_type` + `score`
- Clique: mostrar todas as conexões do nó (highlight de vizinhos)
- Os nós do highlight são os entity IDs do formato `entity:N` — mapear `detected_entities` para esses IDs
- Para o highlight, usar `sigma.plugins.animateNodes` não existe mais no v2 — usar abordagem alternativa: filtrar o grafo ou usar reducer de cor

## Validação

- `pytest -x` deve continuar passando (sem regressões)
- Abrir Streamlit e ver o grafo renderizado
- Nós com cores diferentes por tipo
- Zoom/pan funcionando
- Hover mostra tooltip
- Highlight funciona ao fazer query

## Arquivos-chave

- `/home/petto/brain4me/src/brain4me/graph_cache.py` — `GraphCache`, `get_cached_graphs()`, `get_cache_snapshot()`
- `/home/petto/brain4me/src/brain4me/graphs.py` — `build_knowledge_graph()`, `build_context_graph()`
- `/home/petto/brain4me/app.py` — Streamlit app, 217 linhas
- `/home/petto/brain4me/src/brain4me/storage_schema.py` — schema SQLite com entidades e relações

## Restrições

- NÃO adicionar novas dependências Python — usar apenas CDN para JS
- Sigma.js v2 (não v1, não v3) — a API é significativamente diferente
- Manter compatibilidade com o tema escuro do Streamlit
- O grafo deve funcionar mesmo sem LLM (modo degradado)
