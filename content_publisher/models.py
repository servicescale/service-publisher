from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


@dataclass
class Cluster:
    id: str
    site_id: str
    name: str
    description: str
    priority: int = 50
    atom_ids: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Cluster":
        return cls(**data)


@dataclass
class Atom:
    id: str
    site_id: str
    cluster_id: str
    topic: str
    search_intent: str
    context: dict[str, Any]
    priority: int = 50
    state: str = "planned"
    source_refs: list[dict[str, Any]] = field(default_factory=list)
    output_ids: list[str] = field(default_factory=list)
    signal_ids: list[str] = field(default_factory=list)
    insight_ids: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Atom":
        return cls(**data)


@dataclass
class Output:
    id: str
    site_id: str
    atom_id: str
    channel: str
    kind: str
    title: str
    body: str
    status: str = "draft"
    metadata: dict[str, Any] = field(default_factory=dict)
    published_at: str | None = None
    signal_ids: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Output":
        return cls(**data)


@dataclass
class Signal:
    id: str
    site_id: str
    output_id: str
    kind: str
    value: float
    captured_at: str
    dimensions: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Signal":
        return cls(**data)


@dataclass
class Insight:
    id: str
    site_id: str
    scope: str
    scope_id: str
    kind: str
    summary: str
    evidence: dict[str, Any]
    impact_score: float
    created_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Insight":
        return cls(**data)


@dataclass
class Product:
    id: str
    site_id: str
    title: str
    url: str
    price: str = ""
    merchant: str = ""
    tags: list[str] = field(default_factory=list)
    description: str = ""
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Product":
        return cls(**data)


@dataclass
class StageRun:
    stage: str
    started_at: str
    completed_at: str
    status: str
    counts: dict[str, int] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StageRun":
        return cls(**data)


@dataclass
class LoopRun:
    id: str
    site_id: str
    run_number: int
    started_at: str
    completed_at: str | None = None
    status: str = "running"
    stage_runs: list[StageRun] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LoopRun":
        stage_runs = [StageRun.from_dict(item) for item in data.get("stage_runs", [])]
        payload = dict(data)
        payload["stage_runs"] = stage_runs
        return cls(**payload)


@dataclass
class SiteSummary:
    site_id: str
    loop_runs: int
    cluster_count: int
    atom_count: int
    output_count: int
    signal_count: int
    insight_count: int
    channel_output_counts: dict[str, int]
    signal_totals: dict[str, float]
    signal_source_totals: dict[str, float]
    top_clusters: list[dict[str, Any]]
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SiteSummary":
        return cls(**data)


@dataclass
class Site:
    id: str
    name: str
    niche_focus: str
    target_audience: str
    brand_tone: str
    monetization_strategy: str
    publishing_channels: list[str]
    opportunity_pool: list[dict[str, Any]] = field(default_factory=list)
    cluster_ids: list[str] = field(default_factory=list)
    atom_ids: list[str] = field(default_factory=list)
    output_ids: list[str] = field(default_factory=list)
    product_ids: list[str] = field(default_factory=list)
    signal_ids: list[str] = field(default_factory=list)
    insight_ids: list[str] = field(default_factory=list)
    loop_history: list[LoopRun] = field(default_factory=list)
    loop_runs: int = 0
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Site":
        return cls(**data)


@dataclass
class SiteSnapshot:
    site: Site
    clusters: dict[str, Cluster] = field(default_factory=dict)
    atoms: dict[str, Atom] = field(default_factory=dict)
    outputs: dict[str, Output] = field(default_factory=dict)
    products: dict[str, Product] = field(default_factory=dict)
    signals: dict[str, Signal] = field(default_factory=dict)
    insights: dict[str, Insight] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "site": self.site.to_dict(),
            "clusters": {key: value.to_dict() for key, value in self.clusters.items()},
            "atoms": {key: value.to_dict() for key, value in self.atoms.items()},
            "outputs": {key: value.to_dict() for key, value in self.outputs.items()},
            "products": {key: value.to_dict() for key, value in self.products.items()},
            "signals": {key: value.to_dict() for key, value in self.signals.items()},
            "insights": {key: value.to_dict() for key, value in self.insights.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SiteSnapshot":
        site_data = dict(data["site"])
        site_data["loop_history"] = [LoopRun.from_dict(item) for item in site_data.get("loop_history", [])]
        return cls(
            site=Site.from_dict(site_data),
            clusters={key: Cluster.from_dict(value) for key, value in data.get("clusters", {}).items()},
            atoms={key: Atom.from_dict(value) for key, value in data.get("atoms", {}).items()},
            outputs={key: Output.from_dict(value) for key, value in data.get("outputs", {}).items()},
            products={key: Product.from_dict(value) for key, value in data.get("products", {}).items()},
            signals={key: Signal.from_dict(value) for key, value in data.get("signals", {}).items()},
            insights={key: Insight.from_dict(value) for key, value in data.get("insights", {}).items()},
        )
