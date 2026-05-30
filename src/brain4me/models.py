from dataclasses import dataclass, field


@dataclass(slots=True)
class IngestResult:
    entities_created: int = 0
    relations_created: int = 0
    context_nodes_created: int = 0
    context_edges_created: int = 0
    memory_entries_created: int = 0
    logs_created: int = 0


@dataclass(slots=True)
class ExtractionPayload:
    entity_items: list[tuple[str, str]] = field(default_factory=list)
    context_only_items: list[tuple[str, str, str]] = field(default_factory=list)
    method: str = "heuristic"
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class TopicExplanation:
    topic: str
    decisions: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)


@dataclass(slots=True)
class EntityExplanation:
    entity: str
    relations: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    context: list[str] = field(default_factory=list)
    history: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SourceReference:
    note_id: str
    source_path: str
    title: str
    label: str


@dataclass(slots=True)
class GraphContext:
    entities: list[str] = field(default_factory=list)
    relations: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    inferences: list[str] = field(default_factory=list)
    context_nodes: list[str] = field(default_factory=list)


@dataclass
class AnswerResult:
    question: str
    answer: str
    degraded: bool
    sources: list[SourceReference]
    structured: TopicExplanation | EntityExplanation
    intent: str = "exploration"
    justification: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    detected_entities: list[str] = field(default_factory=list)
    suggested_decision: str = ""
    memories: list[str] = field(default_factory=list)
    context_text: str = ""
    db_path: str = ""
    trace_id: str = ""
