from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from time import time
from typing import Any

import networkx as nx

from .graphs import build_context_graph, build_knowledge_graph
from .metrics import log_metric


@dataclass
class GraphCache:
    kg: nx.DiGraph | None = None
    context_graph: nx.DiGraph | None = None
    last_loaded_at: float | None = None
    db_path: str = ""
    cache_key: tuple[float, int] | None = None
    cache_hit: bool = False
    ttl_seconds: int = 60


_GRAPH_CACHES: dict[str, GraphCache] = {}


def _same_graph_content(left: nx.DiGraph | None, right: nx.DiGraph | None) -> bool:
    if left is None or right is None:
        return False
    return (
        dict(left.nodes(data=True)) == dict(right.nodes(data=True))
        and {(source, target): data for source, target, data in left.edges(data=True)}
        == {(source, target): data for source, target, data in right.edges(data=True)}
    )


def _normalize_db_path(db_path: str | Path) -> str:
    return str(Path(db_path).resolve())


def load_graphs(db_path: str | Path) -> GraphCache:
    normalized_db_path = _normalize_db_path(db_path)
    db_stat = os.stat(normalized_db_path)
    cache = GraphCache(
        kg=build_knowledge_graph(normalized_db_path),
        context_graph=build_context_graph(normalized_db_path),
        last_loaded_at=time(),
        db_path=normalized_db_path,
        cache_key=(db_stat.st_mtime, db_stat.st_size),
        cache_hit=False,
    )
    _GRAPH_CACHES[normalized_db_path] = cache
    return cache


def get_cached_graphs(db_path: str | Path, ttl_seconds: int = 60) -> GraphCache:
    normalized_db_path = _normalize_db_path(db_path)
    now = time()
    cache = _GRAPH_CACHES.get(normalized_db_path)
    db_stat = os.stat(normalized_db_path)
    cache_key = (db_stat.st_mtime, db_stat.st_size)
    cache_is_complete = (
        cache is not None
        and cache.kg is not None
        and cache.context_graph is not None
        and cache.last_loaded_at is not None
    )
    cache_age_within_ttl = cache_is_complete and (now - cache.last_loaded_at) <= ttl_seconds

    if (
        cache_is_complete
        and cache.cache_key == cache_key
        and cache_age_within_ttl
    ):
        cache.cache_hit = True
        cache.ttl_seconds = ttl_seconds
        log_metric("graph_cache_hit", 1.0)
        log_metric("graph_cache_age_seconds", now - cache.last_loaded_at)
        return cache

    previous_cache = cache
    cache = load_graphs(normalized_db_path)
    cache.ttl_seconds = ttl_seconds
    cache.cache_hit = (
        previous_cache is not None
        and cache_age_within_ttl
        and previous_cache.cache_key != cache_key
        and _same_graph_content(previous_cache.kg, cache.kg)
        and _same_graph_content(previous_cache.context_graph, cache.context_graph)
    )
    log_metric("graph_cache_hit", 1.0 if cache.cache_hit else 0.0)
    log_metric("graph_cache_age_seconds", 0.0)
    return cache


def invalidate_cache(db_path: str | Path | None = None) -> None:
    if db_path is None:
        _GRAPH_CACHES.clear()
        return
    _GRAPH_CACHES.pop(_normalize_db_path(db_path), None)


def get_cache_snapshot(db_path: str | Path | None = None) -> dict[str, Any]:
    if db_path is not None:
        cache = _GRAPH_CACHES.get(_normalize_db_path(db_path))
        caches = [cache] if cache is not None else []
    else:
        caches = list(_GRAPH_CACHES.values())

    if not caches:
        return {
            "loaded": False,
            "entries": 0,
            "cache_hit": False,
        }

    latest = max(caches, key=lambda item: float(item.last_loaded_at or 0.0))
    return {
        "loaded": True,
        "entries": len(caches),
        "db_path": latest.db_path,
        "cache_hit": latest.cache_hit,
        "last_loaded_at": latest.last_loaded_at,
        "ttl_seconds": latest.ttl_seconds,
        "knowledge_nodes": latest.kg.number_of_nodes() if latest.kg is not None else 0,
        "knowledge_edges": latest.kg.number_of_edges() if latest.kg is not None else 0,
        "context_nodes": latest.context_graph.number_of_nodes() if latest.context_graph is not None else 0,
        "context_edges": latest.context_graph.number_of_edges() if latest.context_graph is not None else 0,
    }
