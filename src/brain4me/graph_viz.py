"""Interactive graph visualization using Sigma.js v2.

Converts the knowledge graph (nx.DiGraph) to a self-contained HTML page
with Sigma.js v2 rendering, ForceAtlas2-style layout, and interactive
features (hover tooltip, click neighbor highlight, zoom/pan).
"""

from __future__ import annotations

import json
from typing import Any

from .graph_cache import GraphCache

ENTITY_COLORS: dict[str, str] = {
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

DEFAULT_COLOR = "#94a3b8"
NODE_MIN_SIZE = 4
NODE_MAX_SIZE = 20


def _node_to_dict(node_id: str, data: dict[str, Any], max_score: float) -> dict:
    """Convert a networkx node to the graphology JSON format."""
    raw_score = float(data.get("score", 0.5))
    # Normalize score to 0-1 range, default to 0.5 if no max
    norm_score = raw_score / max_score if max_score > 0 else 0.5
    return {
        "key": node_id,
        "attributes": {
            "label": data.get("label", node_id),
            "entity_type": data.get("entity_type", "unknown"),
            "score": round(norm_score, 4),
        },
    }


def _edge_to_dict(
    source: str, target: str, data: dict[str, Any], max_score: float
) -> dict:
    """Convert a networkx edge to the graphology JSON format."""
    raw_score = float(data.get("score", 0.5))
    norm_score = raw_score / max_score if max_score > 0 else 0.5
    return {
        "source": source,
        "target": target,
        "attributes": {
            "predicate": data.get("predicate", "related_to"),
            "score": round(norm_score, 4),
        },
    }


def _resolve_highlight_nodes(
    kg, highlight_entities: list[str] | None
) -> list[str]:
    """Map entity names to graph node IDs (entity:N format).

    Tries exact label match first, then substring match.
    Already-prefixed IDs (entity:*) pass through unchanged.
    """
    if not highlight_entities:
        return []
    matched: list[str] = []
    seen: set[str] = set()

    for entity_name in highlight_entities:
        if not entity_name:
            continue
        # Already a node ID
        if entity_name.startswith("entity:"):
            if entity_name not in seen and entity_name in kg:
                matched.append(entity_name)
                seen.add(entity_name)
            continue

        # Exact label match
        found = False
        for node_id, node_data in kg.nodes(data=True):
            label = node_data.get("label", "")
            if entity_name == label:
                if node_id not in seen:
                    matched.append(node_id)
                    seen.add(node_id)
                found = True
                break
        if found:
            continue

        # Fuzzy / substring match
        en_lower = entity_name.lower().strip()
        for node_id, node_data in kg.nodes(data=True):
            label = node_data.get("label", "")
            if en_lower and (en_lower in label.lower() or label.lower() in en_lower):
                if node_id not in seen:
                    matched.append(node_id)
                    seen.add(node_id)
                break

    return matched


def _build_sigma_html(
    graph_json: str,
    highlight_keys: list[str],
    entity_colors_json: str,
    height: int,
) -> str:
    """Generate a self-contained HTML page with Sigma.js v2."""
    highlight_json = json.dumps(highlight_keys)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Knowledge Graph</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ background: #0e1117; overflow: hidden; }}
#sigma-container {{
    width: 100%; height: {height}px; position: relative;
    background: #0e1117;
}}
#tooltip {{
    position: absolute; display: none; pointer-events: none; z-index: 100;
    background: rgba(15, 17, 23, 0.95); color: #e2e8f0; font-size: 13px;
    padding: 8px 12px; border-radius: 8px; border: 1px solid #334155;
    max-width: 300px; line-height: 1.5; font-family: 'Segoe UI', system-ui, sans-serif;
    backdrop-filter: blur(6px); box-shadow: 0 4px 16px rgba(0,0,0,0.3);
}}
#tooltip .tt-label {{ font-weight: 600; color: #f1f5f9; font-size: 14px; }}
#tooltip .tt-meta {{ color: #94a3b8; font-size: 12px; margin-top: 2px; }}
#tooltip .tt-type {{
    display: inline-block; font-size: 11px; padding: 1px 6px;
    border-radius: 4px; margin-top: 4px;
}}
#status {{
    position: absolute; bottom: 12px; left: 12px; z-index: 10;
    color: #475569; font-size: 11px; font-family: 'Segoe UI', sans-serif;
}}
</style>
</head>
<body>
<div id="sigma-container">
    <div id="tooltip"></div>
    <div id="status">Force layout running…</div>
</div>

<script src="https://cdn.jsdelivr.net/npm/sigma@2.4.0/build/sigma.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/graphology@0.25.4/dist/graphology.umd.min.js"></script>

<script>
(function() {{
    'use strict';

    var COLORS = {entity_colors_json};
    var DEFAULT_COLOR = "{DEFAULT_COLOR}";

    var graphData = {graph_json};
    var initialHighlightSet = new Set({highlight_json});
    var highlightSet = new Set(initialHighlightSet);
    var hasHighlight = initialHighlightSet.size > 0;

    var Graph = graphology.Graph;
    var Sigma = sigma.Sigma;

    var graph = new Graph({{ multi: false, type: 'directed' }});

    // --- Add nodes ---
    graphData.nodes.forEach(function(n) {{
        var attrs = n.attributes || {{}};
        var etype = attrs.entity_type || 'unknown';
        var color = COLORS[etype] || DEFAULT_COLOR;
        var score = parseFloat(attrs.score) || 0.5;
        var size = Math.max({NODE_MIN_SIZE}, Math.min({NODE_MAX_SIZE}, score * {NODE_MAX_SIZE}));
        graph.addNode(n.key, {{
            label: attrs.label || n.key,
            entity_type: etype,
            score: score,
            size: size,
            color: color,
            x: Math.random() * 10 - 5,
            y: Math.random() * 10 - 5,
        }});
    }});

    // --- Add edges ---
    graphData.edges.forEach(function(e, i) {{
        if (!graph.hasNode(e.source) || !graph.hasNode(e.target)) return;
        var attrs = e.attributes || {{}};
        var score = parseFloat(attrs.score) || 0.5;
        graph.addEdgeWithKey('e' + i, e.source, e.target, {{
            label: attrs.predicate || '',
            score: score,
            size: Math.max(0.5, Math.min(6, score * 6)),
            color: '#475569',
        }});
    }});

    // --- Simple force-directed layout (no external dependency) ---
    (function runForceLayout(g, iterations) {{
        var nodes = g.nodes();
        var repulsion = 8.0;
        var attraction = 0.008;
        var damping = 0.4;
        var centerGravity = 0.02;

        for (var it = 0; it < iterations; it++) {{
            var forces = {{}};
            nodes.forEach(function(n) {{ forces[n] = {{x: 0, y: 0}}; }});

            // Repulsion: all pairs
            for (var i = 0; i < nodes.length; i++) {{
                for (var j = i + 1; j < nodes.length; j++) {{
                    var na = nodes[i], nb = nodes[j];
                    var dx = g.getNodeAttribute(na, 'x') - g.getNodeAttribute(nb, 'x');
                    var dy = g.getNodeAttribute(na, 'y') - g.getNodeAttribute(nb, 'y');
                    var dist = Math.sqrt(dx*dx + dy*dy) || 1;
                    var f = repulsion / (dist + 0.1);
                    forces[na].x += f * dx / dist;
                    forces[na].y += f * dy / dist;
                    forces[nb].x -= f * dx / dist;
                    forces[nb].y -= f * dy / dist;
                }}
            }}

            // Attraction: along edges
            g.forEachEdge(function(edge, attrs, source, target) {{
                var dx = g.getNodeAttribute(source, 'x') - g.getNodeAttribute(target, 'x');
                var dy = g.getNodeAttribute(source, 'y') - g.getNodeAttribute(target, 'y');
                var dist = Math.sqrt(dx*dx + dy*dy) || 1;
                var f = attraction * dist;
                var weight = attrs.score || 1;
                forces[source].x -= f * dx / dist * weight;
                forces[source].y -= f * dy / dist * weight;
                forces[target].x += f * dx / dist * weight;
                forces[target].y += f * dy / dist * weight;
            }});

            // Center gravity
            nodes.forEach(function(n) {{
                var x = g.getNodeAttribute(n, 'x');
                var y = g.getNodeAttribute(n, 'y');
                forces[n].x -= centerGravity * x;
                forces[n].y -= centerGravity * y;
            }});

            // Apply forces
            nodes.forEach(function(n) {{
                var x = g.getNodeAttribute(n, 'x');
                var y = g.getNodeAttribute(n, 'y');
                g.setNodeAttribute(n, 'x', x + damping * forces[n].x);
                g.setNodeAttribute(n, 'y', y + damping * forces[n].y);
            }});
        }}
    }})(graph, 120);

    document.getElementById('status').textContent =
        graphData.nodes.length + ' nodes, ' + graphData.edges.length + ' edges';

    // --- Sigma renderer ---
    var container = document.getElementById('sigma-container');
    var tooltip = document.getElementById('tooltip');

    var renderer = new Sigma(graph, container, {{
        renderEdgeLabels: true,
        labelRenderedSizeThreshold: 8,
        edgeLabelRenderedSizeThreshold: 10,
        defaultEdgeLabelColor: '#64748b',
        edgeLabelSize: 10,
        edgeLabelFont: 'Segoe UI, system-ui, sans-serif',
        defaultEdgeType: 'arrow',
        edgeColor: {{ attribute: 'color' }},
        defaultNodeLabelColor: '#cbd5e1',
        labelFont: 'Segoe UI, system-ui, sans-serif',
        labelSize: 12,
        labelRenderedSizeThreshold: 6,
        // Node reducer: dim non-highlighted nodes
        nodeReducer: function(node, data) {{
            if (hasHighlight && !highlightSet.has(node)) {{
                return {{
                    ...data,
                    color: '#1e293b',
                    size: data.size * 0.25,
                    label: '',
                    forceLabel: false,
                }};
            }}
            return data;
        }},
        // Edge reducer: dim/hide non-highlighted edges
        edgeReducer: function(edge, data) {{
            if (hasHighlight) {{
                var source = graph.source(edge);
                var target = graph.target(edge);
                if (!highlightSet.has(source) && !highlightSet.has(target)) {{
                    return {{
                        ...data,
                        color: '#1a1f2e',
                        size: 0.3,
                        label: '',
                        hidden: true,
                    }};
                }}
            }}
            return data;
        }},
    }});

    // --- Hover: tooltip ---
    var hoveredNode = null;
    renderer.on('enterNode', function(e) {{
        hoveredNode = e.node;
        var data = graph.getNodeAttributes(e.node);
        var etype = data.entity_type || 'unknown';
        var typeColor = COLORS[etype] || DEFAULT_COLOR;
        tooltip.innerHTML =
            '<div class="tt-label">' + escapeHtml(data.label || e.node) + '</div>' +
            '<div class="tt-type" style="background:' + typeColor + '22;color:' + typeColor + '">' +
            escapeHtml(etype) + '</div>' +
            '<div class="tt-meta">Score: ' + (data.score || 0).toFixed(3) + '</div>';
        tooltip.style.display = 'block';
    }});
    renderer.on('leaveNode', function() {{
        hoveredNode = null;
        tooltip.style.display = 'none';
    }});

    container.addEventListener('mousemove', function(ev) {{
        if (!hoveredNode) return;
        var rect = container.getBoundingClientRect();
        tooltip.style.left = (ev.clientX - rect.left + 14) + 'px';
        tooltip.style.top = (ev.clientY - rect.top - 10) + 'px';
        // Flip below if too close to top
        if (ev.clientY - rect.top < 60) {{
            tooltip.style.top = (ev.clientY - rect.top + 20) + 'px';
        }}
    }});

    // --- Click node: highlight neighbors ---
    renderer.on('clickNode', function(e) {{
        var clicked = e.node;
        // Toggle: if already solo-highlighting this node, reset
        if (hasHighlight && highlightSet.size === 1 && highlightSet.has(clicked)) {{
            hasHighlight = false;
        }} else {{
            var nh = new Set([clicked]);
            graph.forEachNeighbor(clicked, function(neighbor) {{
                nh.add(neighbor);
            }});
            highlightSet = nh;
            hasHighlight = true;
        }}
        renderer.refresh();
    }});

    // --- Click stage (background): reset to initial highlight ---
    renderer.on('clickStage', function() {{
        highlightSet = new Set(initialHighlightSet);
        hasHighlight = initialHighlightSet.size > 0;
        renderer.refresh();
    }});

    // Utility
    function escapeHtml(str) {{
        var div = document.createElement('div');
        div.appendChild(document.createTextNode(str));
        return div.innerHTML;
    }}

    // Auto-zoom to fit all nodes after layout
    renderer.getCamera().animatedReset({{ duration: 600 }});
}})();
</script>
</body>
</html>"""


def build_graph_html(
    cache: GraphCache,
    highlight_entities: list[str] | None = None,
    height: int = 600,
) -> str:
    """Build a self-contained HTML page visualizing the knowledge graph.

    Parameters
    ----------
    cache :
        GraphCache with a loaded knowledge graph (``cache.kg``).
    highlight_entities :
        Optional list of entity names/labels to highlight initially.
        Matched against node labels in the graph.
    height :
        CSS height in pixels for the graph container.

    Returns
    -------
    str
        Self-contained HTML page, or empty string if the graph is empty.
    """
    kg = cache.kg
    if kg is None or kg.number_of_nodes() == 0:
        return ""

    # Compute max scores for normalization
    max_node_score: float = max(
        (float(d.get("score", 0.5)) for _, d in kg.nodes(data=True)),
        default=0.5,
    )
    max_edge_score: float = max(
        (float(d.get("score", 0.5)) for _, _, d in kg.edges(data=True)),
        default=0.5,
    )
    max_score = max(max_node_score, max_edge_score, 1.0)

    nodes = [
        _node_to_dict(nid, nd, max_score) for nid, nd in kg.nodes(data=True)
    ]
    edges = [
        _edge_to_dict(s, t, ed, max_score)
        for s, t, ed in kg.edges(data=True)
    ]

    graph_data = {"nodes": nodes, "edges": edges}
    graph_json = json.dumps(graph_data, ensure_ascii=False)
    entity_colors_json = json.dumps(ENTITY_COLORS, ensure_ascii=False)

    highlight_keys = _resolve_highlight_nodes(kg, highlight_entities)
    return _build_sigma_html(graph_json, highlight_keys, entity_colors_json, height)
